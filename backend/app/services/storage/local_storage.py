from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.services.storage.base import Storage, StoredObject


class LocalStorage(Storage):
    """File-system backed storage. Good for dev and single-host deployments."""

    name = "local"

    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Disallow `..` escape.
        safe = key.replace("\\", "/")
        if ".." in Path(safe).parts:
            raise ValueError(f"invalid key: {key}")
        p = (self.root / safe).resolve()
        if self.root not in p.parents and p != self.root:
            raise ValueError(f"key escapes root: {key}")
        return p

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        path = self._path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)

        await asyncio.to_thread(_write)
        return StoredObject(key=key, size=len(data), content_type=content_type)

    async def get_object(self, key: str) -> bytes:
        path = self._path(key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete_object(self, key: str) -> None:
        path = self._path(key)

        def _del() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(_del)
