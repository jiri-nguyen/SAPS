"""SAPS-34 spike orchestrator: Dramatiq AsyncIO + SQLAlchemy async, redelivery, sweeper + lock."""
import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid

import redis
from sqlalchemy import text

from spike.db import get_engine, reset_schema, scalar
from spike.tasks import process_invoice, slow_actor

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv", "bin")
LOGS = os.path.join(HERE, "logs")
os.makedirs(LOGS, exist_ok=True)
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def start(cmd: list[str], log: str, **env) -> subprocess.Popen:
    e = {**os.environ, **{k: str(v) for k, v in env.items()}, "PYTHONPATH": HERE}
    return subprocess.Popen(cmd, cwd=HERE, env=e, stdout=open(os.path.join(LOGS, log), "w"),
                            stderr=subprocess.STDOUT, start_new_session=True)


def worker(log: str, processes=1, threads=4, **env) -> subprocess.Popen:
    return start([f"{VENV}/dramatiq", "spike.tasks", "--processes", str(processes),
                  "--threads", str(threads)], log, **env)


def stop(p: subprocess.Popen, sig=signal.SIGTERM) -> None:
    try:
        os.killpg(p.pid, sig)
    except ProcessLookupError:
        pass
    try:
        p.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)


async def new_invoice(status="UPLOADED", age_seconds=0) -> str:
    async with get_engine().begin() as conn:
        return str(await conn.scalar(text(
            "INSERT INTO invoice (id, status, updated_at) VALUES (:i, :s, now() - make_interval(secs => :a)) RETURNING id"),
            {"i": uuid.uuid4(), "s": status, "a": age_seconds}))


async def wait_until(sql: str, expected, timeout: float, **params) -> tuple[bool, float]:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if await scalar(sql, **params) == expected:
            return True, time.monotonic() - t0
        await asyncio.sleep(0.5)
    return False, time.monotonic() - t0


async def fresh() -> None:
    redis.Redis(port=56379).flushall()
    await reset_schema()


async def check_1a_1b() -> None:
    await fresh()
    w = worker("w1ab.log", processes=2, threads=4, CANCEL_LOG=os.path.join(LOGS, "cancel.log"))
    await asyncio.sleep(3)
    # 1a: 20 invoices, every message sent twice (simulates redelivery / sweeper re-send)
    ids = [await new_invoice() for _ in range(20)]
    for i in ids:
        process_invoice.send(i)
        process_invoice.send(i)
    ok, secs = await wait_until("SELECT count(*) FROM invoice WHERE status='PENDING_REVIEW'", 20, 30)
    processed = await scalar("SELECT count(*) FROM invoice_event WHERE action='PROCESSED'")
    max_per = await scalar("SELECT coalesce(max(c),0) FROM (SELECT count(*) c FROM invoice_event "
                           "WHERE action='PROCESSED' GROUP BY invoice_id) x")
    record("1a async actor + SQLAlchemy async, idempotent under duplicates",
           ok and processed == 20 and max_per == 1,
           f"20 invoices, 40 messages, 2 processes x 4 threads -> {processed} processed, "
           f"max {max_per} per invoice, {secs:.1f}s")

    # 1b: time limit 2 s on a 5 s coroutine
    slow_actor.send("t1", 5)
    await asyncio.sleep(8)
    started = await scalar("SELECT count(*) FROM marker WHERE tag='t1' AND stage='started'")
    in_tx = await scalar("SELECT count(*) FROM marker WHERE tag='t1' AND stage='in-transaction'")
    finished = await scalar("SELECT count(*) FROM marker WHERE tag='t1' AND stage='finished'")
    cancelled = os.path.exists(os.path.join(LOGS, "cancel.log")) and "t1 cancelled" in open(os.path.join(LOGS, "cancel.log")).read()
    idle_tx = await scalar("SELECT count(*) FROM pg_stat_activity WHERE datname='saps' AND state LIKE 'idle in transaction%'")
    wlog = open(os.path.join(LOGS, "w1ab.log")).read()
    tle = "TimeLimitExceeded" in wlog
    i2 = await new_invoice()
    process_invoice.send(i2)
    ok2, _ = await wait_until("SELECT status FROM invoice WHERE id=:i", "PENDING_REVIEW", 10, i=i2)
    record("1b time limit cancels the coroutine and rolls back its transaction",
           started == 1 and in_tx == 0 and finished == 0 and cancelled and tle and idle_tx == 0 and ok2,
           f"TimeLimitExceeded logged={tle}, CancelledError seen={cancelled}, committed 'started'={started}, "
           f"uncommitted row rolled back={in_tx == 0}, 'finished'={finished}, idle-in-tx conns={idle_tx}, "
           f"next job OK={ok2}")
    stop(w)


async def check_1c(chance: int = 1_000_000, hb: int = 5000, label: str = "1c") -> None:
    await fresh()
    env = dict(HEARTBEAT_TIMEOUT_MS=hb, MAINTENANCE_CHANCE=chance)
    w1 = worker("w1c-first.log", threads=2, **env)
    await asyncio.sleep(3)
    inv = await new_invoice()
    process_invoice.send(inv, 15)
    await asyncio.sleep(4)
    locked = await scalar("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid "
                          "WHERE a.datname='saps' AND l.mode='RowShareLock'")
    stop(w1, signal.SIGKILL)                      # crash: no ack, no graceful shutdown
    t_kill = time.monotonic()
    w2 = worker("w1c-second.log", threads=2, **env)
    ok, _ = await wait_until("SELECT status FROM invoice WHERE id=:i", "PENDING_REVIEW", 240, i=inv)
    delay = time.monotonic() - t_kill
    processed = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='PROCESSED'", i=inv)
    record(f"{label} crash mid-job -> message redelivered, processed once (maintenance_chance={chance}, heartbeat={hb} ms)",
           ok and processed == 1,
           f"worker killed (SIGKILL) during a 15 s job (row lock held={locked > 0}); new worker finished it "
           f"{delay:.1f}s after the crash (includes 15 s of work); PROCESSED events={processed}")
    stop(w2)


async def check_2() -> None:
    await fresh()
    w = worker("w2.log", threads=2)
    a = start([f"{VENV}/python", "-m", "spike.sweeper", "sweeper-A"], "sweeper-A.log")
    b = start([f"{VENV}/python", "-m", "spike.sweeper", "sweeper-B"], "sweeper-B.log")
    await asyncio.sleep(3)
    stuck = await new_invoice(age_seconds=60)      # saved, but its message was "lost"
    normal = await new_invoice()
    process_invoice.send(normal)                   # normal path, must not be re-sent
    ok, _ = await wait_until("SELECT status FROM invoice WHERE id=:i", "PENDING_REVIEW", 20, i=stuck)
    await asyncio.sleep(6)
    for p in (a, b, w):
        stop(p)
    resent_stuck = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='SWEEPER_RESENT'", i=stuck)
    resent_normal = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='SWEEPER_RESENT'", i=normal)
    processed = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='PROCESSED'", i=stuck)
    logs = {n: open(os.path.join(LOGS, f"sweeper-{n}.log")).read() for n in "AB"}
    acq = {n: logs[n].count("lock acquired") for n in "AB"}
    skip = {n: logs[n].count("-> skip") for n in "AB"}
    record("2 sweeper re-sends stuck invoice; advisory lock lets one instance sweep per tick",
           ok and resent_stuck == 1 and resent_normal == 0 and processed == 1 and sum(skip.values()) > 0,
           f"stuck invoice processed={ok}, re-sent {resent_stuck}x, processed {processed}x; normal invoice re-sent "
           f"{resent_normal}x; ticks with lock A={acq['A']} B={acq['B']}, skipped A={skip['A']} B={skip['B']}")


async def check_1d() -> None:
    """Default broker settings + sweeper: crash recovery must not depend on broker maintenance."""
    await fresh()
    w1 = worker("w1d-first.log", threads=2)
    sw = start([f"{VENV}/python", "-m", "spike.sweeper", "sweeper-D"], "sweeper-D.log")
    await asyncio.sleep(3)
    inv = await new_invoice()
    process_invoice.send(inv, 15)
    await asyncio.sleep(6)                          # job running: row locked -> sweeper must skip it
    resent_while_running = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='SWEEPER_RESENT'", i=inv)
    stop(w1, signal.SIGKILL)
    t_kill = time.monotonic()
    w2 = worker("w1d-second.log", threads=2)
    ok, _ = await wait_until("SELECT status FROM invoice WHERE id=:i", "PENDING_REVIEW", 90, i=inv)
    delay = time.monotonic() - t_kill
    processed = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='PROCESSED'", i=inv)
    resent = await scalar("SELECT count(*) FROM invoice_event WHERE invoice_id=:i AND action='SWEEPER_RESENT'", i=inv)
    record("1d crash with DEFAULT broker settings -> recovered by the sweeper",
           ok and processed == 1 and resent_while_running == 0 and resent >= 1,
           f"sweeper skipped the invoice while its job held the row lock (re-sent while running={resent_while_running}); "
           f"after SIGKILL the sweeper re-sent it {resent}x; finished {delay:.1f}s after the crash (re-sent job uses the default 0.2 s work); "
           f"PROCESSED events={processed}")
    for p in (sw, w2):
        stop(p)


async def main() -> None:
    which = sys.argv[1:] or ["1ab", "1c", "1d", "2"]   # "1c-default" (4 min) only on request
    if "1ab" in which: await check_1a_1b()
    if "1c" in which: await check_1c()
    if "1c-default" in which: await check_1c(chance=1000, hb=60000, label="1c-default")
    if "1d" in which: await check_1d()
    if "2" in which: await check_2()
    print("\nSUMMARY")
    for name, ok, _ in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
