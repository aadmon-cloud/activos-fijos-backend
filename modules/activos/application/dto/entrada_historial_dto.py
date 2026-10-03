from dataclasses import dataclass
from datetime import datetime

from modules.activos.domain.entities import EntradaHistorialActivo


@dataclass
class EntradaHistorialDTO:
    id: str
    activo_id: str
    campo: str
    valor_anterior: str
    valor_nuevo: str
    modificado_por_nombre: str
    modificado_por_fecha: datetime


def entrada_historial_a_dto(entrada: EntradaHistorialActivo) -> EntradaHistorialDTO:
    return EntradaHistorialDTO(
        id=entrada.id,
        activo_id=entrada.activo_id,
        campo=entrada.campo,
        valor_anterior=entrada.valor_anterior,
        valor_nuevo=entrada.valor_nuevo,
        modificado_por_nombre=entrada.modificado_por.nombre,
        modificado_por_fecha=entrada.modificado_por.fecha,
    )
