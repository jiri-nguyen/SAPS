"""SeaweedFS through the S3 API (ADR-0006). boto3 is synchronous, so calls run in a worker thread."""

import asyncio
from collections.abc import AsyncIterator
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

_CHUNK_BYTES = 256 * 1024


class S3FileStorage:
    def __init__(self, *, endpoint_url: str, bucket: str, access_key: str, secret_key: str) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",  # required by the SDK; SeaweedFS ignores it
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def put(self, key: str, data: BinaryIO, content_type: str) -> None:
        """SeaweedFS creates the bucket on first write; on AWS the bucket comes from the infrastructure."""
        await asyncio.to_thread(
            self._client.upload_fileobj, data, self._bucket, key, ExtraArgs={"ContentType": content_type}
        )

    async def get(self, key: str) -> AsyncIterator[bytes]:
        try:
            response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise FileNotFoundError(key) from exc
            raise
        body = response["Body"]
        try:
            while chunk := await asyncio.to_thread(body.read, _CHUNK_BYTES):
                yield bytes(chunk)
        finally:
            await asyncio.to_thread(body.close)

    def read(self, key: str) -> bytes:
        """Whole object at once; for tests and support scripts only (downloads stream through `get`)."""
        body = self._client.get_object(Bucket=self._bucket, Key=key)["Body"]
        return bytes(body.read())
