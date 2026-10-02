import asyncio
import os
from pathlib import Path

from config.settings import settings
from modules.movimientos.application.ports.storage_repository import StorageRepositoryPort


class DiskStorageRepository(StorageRepositoryPort):
    """Guarda archivos en disco, bajo `STORAGE_DIR` (ver `config/settings.py`).
    Decisión de alcance: disco local por ahora (ver MIGRATION_PLAN.md), detrás
    de este puerto para poder reemplazarlo por MinIO/GCS más adelante."""

    def __init__(self, base_dir: str | None = None):
        self._base_dir = Path(base_dir or settings.STORAGE_DIR).resolve()

    async def guardar(self, subcarpeta: str, nombre_archivo: str, contenido: bytes) -> str:
        nombre_seguro = _nombre_seguro(nombre_archivo)
        ruta_relativa = Path(subcarpeta) / nombre_seguro
        destino = self._resolver_dentro_del_base(ruta_relativa)

        def _escribir():
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)

        await asyncio.to_thread(_escribir)
        return ruta_relativa.as_posix()

    async def leer(self, ruta: str) -> bytes:
        destino = self._resolver_dentro_del_base(Path(ruta))
        return await asyncio.to_thread(destino.read_bytes)

    def _resolver_dentro_del_base(self, ruta_relativa: Path) -> Path:
        destino = (self._base_dir / ruta_relativa).resolve()
        if destino != self._base_dir and self._base_dir not in destino.parents:
            raise ValueError(f"Ruta de almacenamiento fuera de STORAGE_DIR: '{ruta_relativa}'")
        return destino


def _nombre_seguro(nombre_archivo: str) -> str:
    """Descarta cualquier componente de directorio del nombre subido (evita
    path traversal vía nombres de archivo con `../` o separadores)."""
    limpio = os.path.basename(nombre_archivo.replace("\\", "/"))
    if not limpio or limpio in {".", ".."}:
        raise ValueError(f"Nombre de archivo inválido: '{nombre_archivo}'")
    return limpio
