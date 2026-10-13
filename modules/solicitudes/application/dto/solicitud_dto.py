from dataclasses import dataclass, field
from datetime import datetime

from modules.solicitudes.application.dto.entrada_seguimiento_dto import (
    EntradaSeguimientoDTO,
    entrada_seguimiento_a_dto,
)
from modules.solicitudes.domain.entities import Solicitud


@dataclass
class SolicitudDTO:
    id: str
    tipo: str
    activo_id: str
    descripcion: str
    prioridad: str
    evidencias: list[str]
    estado: str
    rol_asignado: str | None
    area_id: str | None
    seguimiento: list[EntradaSeguimientoDTO]
    creado_por_id: str
    creado_por_nombre: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None


@dataclass
class SolicitudConNombresDTO(SolicitudDTO):
    activo_nombre: str | None = None
    activo_numero_inventario: str | None = None
    area_nombre: str | None = None
    # Solo el detalle los calcula (dependen de quien consulta); en el listado van vacios.
    estados_permitidos: list[str] = field(default_factory=list)
    puede_comentar: bool = False


@dataclass
class ListadoSolicitudesDTO:
    items: list[SolicitudConNombresDTO]
    total: int
    skip: int
    limit: int


def solicitud_a_dto(solicitud: Solicitud) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud.id,
        tipo=solicitud.tipo.value,
        activo_id=solicitud.activo_id,
        descripcion=solicitud.descripcion,
        prioridad=solicitud.prioridad.value,
        evidencias=solicitud.evidencias,
        estado=solicitud.estado.value,
        rol_asignado=solicitud.rol_asignado,
        area_id=solicitud.area_id,
        seguimiento=[entrada_seguimiento_a_dto(e) for e in solicitud.seguimiento],
        creado_por_id=solicitud.creado_por.id_persona,
        creado_por_nombre=solicitud.creado_por.nombre,
        fecha_creacion=solicitud.creado_por.fecha,
        fecha_actualizacion=(
            solicitud.actualizado_por.fecha if solicitud.actualizado_por else None
        ),
    )
