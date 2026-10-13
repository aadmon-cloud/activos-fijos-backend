from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EstadoNotificacion(str, Enum):
    ENVIADA = "enviada"
    FALLIDA = "fallida"

    # No se intento enviar: nadie con correo a quien avisar, o el correo no esta configurado.
    OMITIDA = "omitida"


@dataclass(frozen=True, kw_only=True)
class Notificacion:
    id: str | None

    # Como se pidio: "usuario:<id>", "rol:<rol>", "area:<id>" o un correo.
    destinatarios: list[str]

    # Correos a los que se envio (o se habria enviado), ya resueltos.
    correos: list[str]
    asunto: str
    cuerpo: str
    estado: EstadoNotificacion
    detalle: str | None
    intentos: int
    creada_en: datetime
    actualizada_en: datetime
