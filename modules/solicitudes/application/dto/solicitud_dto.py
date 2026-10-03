from dataclasses import dataclass

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
    )
