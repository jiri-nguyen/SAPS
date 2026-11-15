---
title: "Spike SAPS-34 — worker queue, sweeper and file storage"
status: approved
owner: "Solution Architect (our company)"
reviewers: []
last_updated: 2026-12-01
related: [SAPS-34, ADR-0004, ADR-0006]
---

# Spike SAPS-34 — worker queue, sweeper and file storage

Throwaway code that verified [ADR-0004](../../docs/02-architecture/adr/0004-process-invoices-in-background-worker.md)
(Dramatiq + Redis) and [ADR-0006](../../docs/02-architecture/adr/0006-store-invoice-files-in-seaweedfs.md) (SeaweedFS).
Linear: [SAPS-34](https://linear.app/jiringuyen/issue/SAPS-34). Results are recorded in the two ADRs; this code is
kept only so the checks can be repeated. It is **not** production code.

## What it checks
| # | Check | Script |
|---|---|---|
| 1a | Async actors with SQLAlchemy async; idempotent under duplicate messages | `run_checks.py 1ab` |
| 1b | Time limit cancels the coroutine and rolls back its transaction | `run_checks.py 1ab` |
| 1c | Worker crash → Redis broker redelivers the message | `run_checks.py 1c` |
| 1c-default | Same with default broker settings (takes about 4 min) | `run_checks.py 1c-default` |
| 1d | Worker crash with default broker settings → recovered by the sweeper | `run_checks.py 1d` |
| 2 | Two sweeper instances; advisory lock; only stuck invoices are re-sent | `run_checks.py 2` |
| 3a–3c | SeaweedFS S3: put/get/delete, presigned URL, persistence | `s3check.py` |

## How to run
Requires Docker and Python 3.13 (with `uv`, or `pip`).

```bash
cd spikes/saps-34
docker compose up -d                       # PostgreSQL 17, Redis 7.2 (AOF), SeaweedFS 4.53
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
PYTHONPATH=. .venv/bin/python run_checks.py          # 1a, 1b, 1c, 1d, 2
.venv/bin/python s3check.py                           # 3a-3c (restarts the seaweedfs container)
docker compose down -v
```

Host ports used: PostgreSQL `55432`, Redis `56379`, SeaweedFS S3 `58333`.
The credentials in `s3.json` and the database password are local test values only.
Logs of each run are written to `logs/` (ignored by git).
