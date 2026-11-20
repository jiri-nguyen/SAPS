from uuid import uuid4

from dramatiq.brokers.stub import StubBroker

from saps.adapters.queue.dramatiq_queue import QUEUE, DramatiqJobQueue


async def test_process_invoice_message_carries_only_the_invoice_id() -> None:
    broker = StubBroker()
    broker.declare_queue(QUEUE)
    invoice_id = uuid4()
    await DramatiqJobQueue(broker).send_process_invoice(invoice_id)
    message = broker.queues[QUEUE].get_nowait()
    assert b'"actor_name":"process_invoice"' in message
    assert f'"args":["{invoice_id}"]'.encode() in message


async def test_process_invoice_actor_runs_the_job(monkeypatch) -> None:
    from saps.worker import actors

    called: list[object] = []

    async def fake_run(invoice_id: object) -> None:
        called.append(invoice_id)

    monkeypatch.setattr(actors, "run_processing", fake_run)
    invoice_id = uuid4()
    await actors.process_invoice.fn.__wrapped__(str(invoice_id))
    assert called == [invoice_id]
