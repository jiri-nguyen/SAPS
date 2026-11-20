"""File Storage Port (ADR-0006). PoC adapter: SeaweedFS through the S3 API."""

from typing import BinaryIO, Protocol


class FileStoragePort(Protocol):
    async def put(self, key: str, data: BinaryIO, content_type: str) -> None:
        """Store `data` (read from its current position) under `key`; replaces an existing object."""
        ...
