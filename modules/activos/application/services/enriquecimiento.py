from modules.activos.application.dto.activo_con_nombres_dto import (
    ActivoConNombresDTO,
    activo_con_nombres_a_dto,
)
from modules.activos.application.dto.activo_dto import activo_a_dto
from modules.activos.application.ports.resolutor_nombres import (
    ReferenciasActivo,
    ResolutorNombresPort,
)
from modules.activos.domain.entities import Activo


async def con_nombres(
    activos: list[Activo], resolutor: ResolutorNombresPort
) -> list[ActivoConNombresDTO]:
    """Convierte activos a DTO resolviendo en una sola pasada los nombres de sus referencias."""
    if not activos:
        return []

    referencias = ReferenciasActivo(
        categoria_ids={a.categoria_id for a in activos},
        area_ids={a.area_id for a in activos},
        responsable_ids={a.responsable_id for a in activos},
        condicion_ids={a.condicion_id for a in activos},
        sede_ids={a.sede_id for a in activos},
        lugar_ids={a.lugar_id for a in activos},
    )
    nombres = await resolutor.resolver(referencias)

    return [activo_con_nombres_a_dto(activo_a_dto(activo), nombres) for activo in activos]
