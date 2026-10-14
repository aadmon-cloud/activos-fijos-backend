from dataclasses import dataclass
from datetime import datetime

from modules.permisos.domain.entities import CambioPermiso


@dataclass(frozen=True)
class CambioPermisoDTO:
    id: str | None
    rol: str
    permiso: str
    accion: str
    por_id: str
    por_nombre: str
    fecha: datetime


def cambio_a_dto(cambio: CambioPermiso) -> CambioPermisoDTO:
    return CambioPermisoDTO(
        id=cambio.id,
        rol=cambio.rol,
        permiso=cambio.permiso,
        accion=cambio.accion.value,
        por_id=cambio.por.id_persona,
        por_nombre=cambio.por.nombre,
        fecha=cambio.por.fecha,
    )
