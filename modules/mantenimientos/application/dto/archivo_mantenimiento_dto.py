from dataclasses import dataclass

from modules.mantenimientos.domain.entities import ArchivoMantenimiento


@dataclass
class ArchivoMantenimientoDTO:
    archivo_id: str
    nombre: str


def archivo_a_dto(archivo: ArchivoMantenimiento) -> ArchivoMantenimientoDTO:
    return ArchivoMantenimientoDTO(archivo_id=archivo.archivo_id, nombre=archivo.nombre)
