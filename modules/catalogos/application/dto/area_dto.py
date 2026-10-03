from dataclasses import dataclass

from modules.catalogos.domain.entities import Area


@dataclass
class AreaDTO:
    id: str
    nombre: str
    descripcion: str | None


def area_a_dto(area: Area) -> AreaDTO:
    return AreaDTO(id=area.id, nombre=area.nombre, descripcion=area.descripcion)
