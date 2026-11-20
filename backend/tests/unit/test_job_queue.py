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


async def test_placeholder_process_invoice_actor_logs_the_message(monkeypatch) -> None:
    from saps.worker import actors

    seen: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(actors.log, "info", lambda msg, extra: seen.append((msg, extra)))
    await actors.process_invoice.fn.__wrapped__("abc")
    assert seen == [("process_invoice_received", {"invoice_id": "abc"})]
