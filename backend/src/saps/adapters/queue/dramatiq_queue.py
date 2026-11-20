"""Job Queue adapter: Dramatiq messages on the SAPS Message Broker (ADR-0004).

The SAPS API only enqueues by actor name; it does not import the SAPS Worker's actors.
"""

import asyncio
from uuid import UUID

import dramatiq
from dramatiq.brokers.redis import RedisBroker

QUEUE = "default"


class DramatiqJobQueue:
    def __init__(self, broker: RedisBroker) -> None:
        self._broker = broker

    async def send_process_invoice(self, invoice_id: UUID) -> None:
        await self._send("process_invoice", invoice_id)

    async def send_rematch_invoice(self, invoice_id: UUID) -> None:
        await self._send("rematch_invoice", invoice_id)

    async def _send(self, actor_name: str, invoice_id: UUID) -> None:
        message: dramatiq.Message[None] = dramatiq.Message(
            queue_name=QUEUE, actor_name=actor_name, args=(str(invoice_id),), kwargs={}, options={}
        )
        await asyncio.to_thread(self._broker.enqueue, message)
