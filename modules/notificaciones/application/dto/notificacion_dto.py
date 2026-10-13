from dataclasses import dataclass
from datetime import datetime

from modules.notificaciones.domain.entities import Notificacion


@dataclass
class NotificacionDTO:
    id: str
    destinatarios: list[str]
    correos: list[str]
    asunto: str
    cuerpo: str
    estado: str
    detalle: str | None
    intentos: int
    creada_en: datetime
    actualizada_en: datetime


@dataclass
class ListadoNotificacionesDTO:
    items: list[NotificacionDTO]
    total: int
    skip: int
    limit: int


def notificacion_a_dto(notificacion: Notificacion) -> NotificacionDTO:
    return NotificacionDTO(
        id=notificacion.id,
        destinatarios=notificacion.destinatarios,
        correos=notificacion.correos,
        asunto=notificacion.asunto,
        cuerpo=notificacion.cuerpo,
        estado=notificacion.estado.value,
        detalle=notificacion.detalle,
        intentos=notificacion.intentos,
        creada_en=notificacion.creada_en,
        actualizada_en=notificacion.actualizada_en,
    )


@dataclass
class ResultadoRecordatoriosDTO:
    mantenimientos_avisados: int | None
    devoluciones_recordadas: int | None

    # Una tarea que falla no impide la otra: su error queda aqui.
    errores: list[str]
