from dataclasses import dataclass, fields

from modules.activos.application.dto.activo_dto import ActivoDTO
from modules.activos.application.ports.resolutor_nombres import NombresReferencias


@dataclass
class ActivoConNombresDTO(ActivoDTO):
    categoria_nombre: str | None
    area_nombre: str | None
    responsable_nombre: str | None
    condicion_nombre: str | None
    condicion_color: str | None
    sede_nombre: str | None
    lugar_nombre: str | None


@dataclass
class ListadoActivosDTO:
    items: list[ActivoConNombresDTO]
    total: int
    skip: int
    limit: int


def activo_con_nombres_a_dto(activo: ActivoDTO, nombres: NombresReferencias) -> ActivoConNombresDTO:
    condicion = nombres.condiciones.get(activo.condicion_id)
    base = {campo.name: getattr(activo, campo.name) for campo in fields(ActivoDTO)}

    return ActivoConNombresDTO(
        **base,
        categoria_nombre=nombres.categorias.get(activo.categoria_id),
        area_nombre=nombres.areas.get(activo.area_id),
        responsable_nombre=nombres.responsables.get(activo.responsable_id),
        condicion_nombre=condicion.nombre if condicion else None,
        condicion_color=condicion.color if condicion else None,
        sede_nombre=nombres.sedes.get(activo.sede_id),
        lugar_nombre=nombres.lugares.get(activo.lugar_id),
    )
