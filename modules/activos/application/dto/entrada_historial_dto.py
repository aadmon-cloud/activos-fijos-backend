from dataclasses import dataclass
from datetime import datetime

from modules.activos.domain.entities import EntradaHistorialActivo


@dataclass
class EntradaHistorialDTO:
    id: str
    activo_id: str
    modificado_por_nombre: str
    modificado_por_fecha: datetime
    tipo: str = "cambio_campo"
    campo: str | None = None
    valor_anterior: str | None = None
    valor_nuevo: str | None = None
    nota: str | None = None
    valor_anterior_nombre: str | None = None
    valor_nuevo_nombre: str | None = None


def entrada_historial_a_dto(entrada: EntradaHistorialActivo) -> EntradaHistorialDTO:
    return EntradaHistorialDTO(
        id=entrada.id,
        activo_id=entrada.activo_id,
        tipo=entrada.tipo,
        campo=entrada.campo,
        valor_anterior=entrada.valor_anterior,
        valor_nuevo=entrada.valor_nuevo,
        nota=entrada.nota,
        modificado_por_nombre=entrada.modificado_por.nombre,
        modificado_por_fecha=entrada.modificado_por.fecha,
    )
