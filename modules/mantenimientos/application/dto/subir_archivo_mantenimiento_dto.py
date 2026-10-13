from dataclasses import dataclass
from typing import Literal


@dataclass
class SubirArchivoMantenimientoDTO:
    id_mantenimiento: str
    nombre: str
    contenido: bytes
    categoria: Literal["documento", "evidencia"]
    actualizado_por_id: str
    actualizado_por_nombre: str
