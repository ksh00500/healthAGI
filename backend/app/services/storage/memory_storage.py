from __future__ import annotations

from app.services.storage.base import Storage, StoredObject


class MemoryStorage(Storage):
    """In-memory storage for tests. Process-singleton."""

    name = "memory"

    def __init__(self) -> None:
        self._blobs: dict[str, tuple[bytes, str]] = {}

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        self._blobs[key] = (data, content_type)
        return StoredObject(key=key, size=len(data), content_type=content_type)

    async def get_object(self, key: str) -> bytes:
        if key not in self._blobs:
            raise FileNotFoundError(key)
        return self._blobs[key][0]

    async def delete_object(self, key: str) -> None:
        self._blobs.pop(key, None)

    def all_keys(self) -> list[str]:
        return list(self._blobs.keys())


_singleton: MemoryStorage | None = None


def get_memory_storage() -> MemoryStorage:
    global _singleton
    if _singleton is None:
        _singleton = MemoryStorage()
    return _singleton


def reset_memory_storage() -> None:
    global _singleton
    _singleton = MemoryStorage()
