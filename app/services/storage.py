import os
import hashlib
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile


class StorageBackend:
    async def save(self, upload: UploadFile) -> Tuple[str, str, int]:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    async def save(self, upload: UploadFile) -> Tuple[str, str, int]:
        filename = os.path.basename(upload.filename or "upload.bin")
        storage_path = Path(self.base_dir) / filename
        counter = 1
        while storage_path.exists():
            stem = storage_path.stem
            suffix = storage_path.suffix
            storage_path = Path(self.base_dir) / f"{stem}-{counter}{suffix}"
            counter += 1

        hasher = hashlib.sha256()
        size = 0
        with storage_path.open("wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
                f.write(chunk)

        await upload.close()
        return str(storage_path), hasher.hexdigest(), size
