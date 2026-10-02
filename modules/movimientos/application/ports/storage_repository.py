from abc import ABC, abstractmethod


class StorageRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, subcarpeta: str, nombre_archivo: str, contenido: bytes) -> str:
        """Persist `contenido` under `subcarpeta`/`nombre_archivo` and return
        the path/key needed to retrieve it later via `leer()`."""

    @abstractmethod
    async def leer(self, ruta: str) -> bytes:
        """Return the raw bytes previously stored at `ruta` (returned by `guardar`)."""
