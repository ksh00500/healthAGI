from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredObject:
    key: str
    size: int
    content_type: str


class Storage(ABC):
    """Object storage backend."""

    name: str = "base"

    @abstractmethod
    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> StoredObject: ...

    @abstractmethod
    async def get_object(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete_object(self, key: str) -> None: ...

    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        """Pre-signed download URL if backend supports it; otherwise None."""
        return None
