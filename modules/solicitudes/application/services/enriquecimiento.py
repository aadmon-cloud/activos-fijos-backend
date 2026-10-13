from dataclasses import fields

from modules.solicitudes.application.dto.solicitud_dto import (
    SolicitudConNombresDTO,
    SolicitudDTO,
    solicitud_a_dto,
)
from modules.solicitudes.application.ports.resolutor_referencias import (
    ReferenciasSolicitud,
    ResolutorReferenciasPort,
)
from modules.solicitudes.domain.entities import Solicitud


async def con_nombres(
    solicitudes: list[Solicitud], resolutor: ResolutorReferenciasPort
) -> list[SolicitudConNombresDTO]:
    """Convierte solicitudes a DTO resolviendo en una sola pasada el activo y el area de cada una."""
    if not solicitudes:
        return []

    nombres = await resolutor.resolver(
        ReferenciasSolicitud(
            activo_ids={s.activo_id for s in solicitudes},
            area_ids={s.area_id for s in solicitudes if s.area_id},
        )
    )

    resultado = []
    for solicitud in solicitudes:
        base: SolicitudDTO = solicitud_a_dto(solicitud)
        activo = nombres.activos.get(solicitud.activo_id)
        resultado.append(
            SolicitudConNombresDTO(
                **{campo.name: getattr(base, campo.name) for campo in fields(SolicitudDTO)},
                activo_nombre=activo.nombre if activo else None,
                activo_numero_inventario=activo.numero_inventario if activo else None,
                area_nombre=nombres.areas.get(solicitud.area_id) if solicitud.area_id else None,
            )
        )

    return resultado
