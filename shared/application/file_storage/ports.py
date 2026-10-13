from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ArchivoAlmacenado:
    nombre: str
    tipo_mime: str
    contenido: bytes


class AlmacenArchivosPort(ABC):
    """Almacenamiento de N archivos por propietario (a diferencia de AlmacenFotosPort de
    activos, que guarda una unica foto por activo)."""

    @abstractmethod
    async def guardar(self, propietario_id: str, nombre: str, contenido: bytes, tipo_mime: str) -> str:
        """Guarda el archivo y retorna su id."""

    @abstractmethod
    async def obtener(self, archivo_id: str) -> ArchivoAlmacenado | None: ...

    @abstractmethod
    async def eliminar(self, archivo_id: str) -> None: ...
