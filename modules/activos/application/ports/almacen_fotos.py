from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class FotoAlmacenada:
    contenido: bytes
    tipo_mime: str


class AlmacenFotosPort(ABC):
    """Almacenamiento de la fotografia de un activo (una por activo)."""

    @abstractmethod
    async def guardar(self, activo_id: str, contenido: bytes, tipo_mime: str) -> None:
        """Guarda la foto, reemplazando la anterior si existe."""

    @abstractmethod
    async def obtener(self, activo_id: str) -> FotoAlmacenada | None: ...

    @abstractmethod
    async def eliminar(self, activo_id: str) -> None: ...
