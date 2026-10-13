from datetime import datetime

from pydantic import BaseModel

from modules.notificaciones.domain.entities import EstadoNotificacion


class NotificacionResponse(BaseModel):
    id: str
    destinatarios: list[str]
    correos: list[str]
    asunto: str
    cuerpo: str
    estado: EstadoNotificacion
    detalle: str | None
    intentos: int
    creada_en: datetime
    actualizada_en: datetime


class EstadoCorreoResponse(BaseModel):
    configurado: bool
    remitente: str | None


class ResultadoRecordatoriosResponse(BaseModel):
    mantenimientos_avisados: int | None
    devoluciones_recordadas: int | None
    errores: list[str]
