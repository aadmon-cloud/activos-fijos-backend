from dataclasses import dataclass

from modules.catalogos.domain.entities import Condicion


@dataclass
class CondicionDTO:
    id: str
    nombre: str
    color: str
    descripcion: str | None


def condicion_a_dto(condicion: Condicion) -> CondicionDTO:
    return CondicionDTO(
        id=condicion.id,
        nombre=condicion.nombre,
        color=condicion.color,
        descripcion=condicion.descripcion,
    )
