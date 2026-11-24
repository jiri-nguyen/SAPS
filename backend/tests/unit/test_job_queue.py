from uuid import uuid4

from dramatiq.brokers.stub import StubBroker

from saps.adapters.queue.dramatiq_queue import QUEUE, DramatiqJobQueue


async def test_process_invoice_message_carries_the_invoice_and_its_company() -> None:  # SAPS-41 BR-06
    broker = StubBroker()
    broker.declare_queue(QUEUE)
    invoice_id, tenant_id = uuid4(), uuid4()
    await DramatiqJobQueue(broker).send_process_invoice(invoice_id, tenant_id)
    message = broker.queues[QUEUE].get_nowait()
    assert b'"actor_name":"process_invoice"' in message
    assert f'"args":["{invoice_id}","{tenant_id}"]'.encode() in message


async def test_process_invoice_actor_runs_the_job(monkeypatch) -> None:
    from saps.worker import actors

    called: list[object] = []

    async def fake_run(invoice_id: object, tenant_id: object) -> None:
        called.append((invoice_id, tenant_id))

    monkeypatch.setattr(actors, "run_processing", fake_run)
    invoice_id, tenant_id = uuid4(), uuid4()
    await actors.process_invoice.fn.__wrapped__(str(invoice_id), str(tenant_id))
    await actors.process_invoice.fn.__wrapped__(str(invoice_id))  # sent before SAPS-41: no company (EC-05)
    assert called == [(invoice_id, tenant_id), (invoice_id, None)]


async def test_rematch_invoice_message_carries_the_invoice_and_its_company() -> None:  # SAPS-20 §3.5, SAPS-41
    broker = StubBroker()
    broker.declare_queue(QUEUE)
    invoice_id, tenant_id = uuid4(), uuid4()
    await DramatiqJobQueue(broker).send_rematch_invoice(invoice_id, tenant_id)
    message = broker.queues[QUEUE].get_nowait()
    assert b'"actor_name":"rematch_invoice"' in message
    assert f'"args":["{invoice_id}","{tenant_id}"]'.encode() in message
