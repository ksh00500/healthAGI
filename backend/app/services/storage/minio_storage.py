from __future__ import annotations

import asyncio
import io
import logging
from datetime import timedelta
from typing import Any

from app.services.storage.base import Storage, StoredObject

logger = logging.getLogger(__name__)


class MinIOStorage(Storage):
    """S3-compatible MinIO backend. Lazy-imports the `minio` SDK."""

    name = "minio"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self.endpoint = endpoint
        self.bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._secure = secure
        self._client: Any | None = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            try:
                from minio import Minio
            except ImportError as e:
                raise RuntimeError(
                    "minio SDK not installed. `pip install minio`"
                ) from e
            client = Minio(
                self.endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )

            def _ensure_bucket() -> None:
                if not client.bucket_exists(self.bucket):
                    client.make_bucket(self.bucket)

            await asyncio.to_thread(_ensure_bucket)
            self._client = client
            return client

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        client = await self._get_client()

        def _put() -> None:
            client.put_object(
                self.bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        await asyncio.to_thread(_put)
        return StoredObject(key=key, size=len(data), content_type=content_type)

    async def get_object(self, key: str) -> bytes:
        client = await self._get_client()

        def _get() -> bytes:
            response = client.get_object(self.bucket, key)
            try:
                data: bytes = response.read()
                return data
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_get)

    async def delete_object(self, key: str) -> None:
        client = await self._get_client()

        def _del() -> None:
            client.remove_object(self.bucket, key)

        await asyncio.to_thread(_del)

    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        if self._client is None:
            return None
        try:
            url: str = self._client.presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expires_seconds)
            )
            return url
        except Exception:  # noqa: BLE001
            logger.exception("failed to make presigned url for %s", key)
            return None
