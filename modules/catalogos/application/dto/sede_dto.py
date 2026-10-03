from dataclasses import dataclass

from modules.catalogos.domain.entities import Sede


@dataclass
class SedeDTO:
    id: str
    nombre: str
    descripcion: str | None


def sede_a_dto(sede: Sede) -> SedeDTO:
    return SedeDTO(id=sede.id, nombre=sede.nombre, descripcion=sede.descripcion)
