from __future__ import annotations

import os

from app.config import get_settings
from app.services.storage.base import Storage
from app.services.storage.local_storage import LocalStorage
from app.services.storage.memory_storage import get_memory_storage
from app.services.storage.minio_storage import MinIOStorage

_singleton: Storage | None = None


def get_storage() -> Storage:
    """Return the configured object storage backend.

    HEALTHAGI_STORAGE_BACKEND in {memory, local, minio}.
    Defaults to minio when settings look like a real MinIO host, else local.
    """
    global _singleton
    backend = os.getenv("HEALTHAGI_STORAGE_BACKEND")
    if backend == "memory":
        return get_memory_storage()
    if _singleton is not None:
        return _singleton

    settings = get_settings()
    if backend == "local" or not backend:
        # Default to local for dev: data/photos under repo root.
        root = os.getenv("HEALTHAGI_LOCAL_STORAGE_DIR", "./data/storage")
        _singleton = LocalStorage(root)
        return _singleton
    if backend == "minio":
        _singleton = MinIOStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
        return _singleton
    raise RuntimeError(f"unknown storage backend: {backend}")
