from dataclasses import dataclass
from datetime import datetime

from modules.solicitudes.domain.entities import EntradaSeguimiento


@dataclass
class EntradaSeguimientoDTO:
    autor_nombre: str
    autor_fecha: datetime
    comentario: str
    estado_anterior: str | None
    estado_nuevo: str | None


def entrada_seguimiento_a_dto(entrada: EntradaSeguimiento) -> EntradaSeguimientoDTO:
    return EntradaSeguimientoDTO(
        autor_nombre=entrada.autor.nombre,
        autor_fecha=entrada.autor.fecha,
        comentario=entrada.comentario,
        estado_anterior=entrada.estado_anterior,
        estado_nuevo=entrada.estado_nuevo,
    )
