from dataclasses import dataclass

from modules.catalogos.domain.entities import Lugar


@dataclass
class LugarDTO:
    id: str
    nombre: str
    tipo: str
    sede_id: str


def lugar_a_dto(lugar: Lugar) -> LugarDTO:
    return LugarDTO(id=lugar.id, nombre=lugar.nombre, tipo=lugar.tipo.value, sede_id=lugar.sede_id)
