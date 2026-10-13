from functools import lru_cache

from modules.notificaciones.application.ports.configuracion_correo import ConfiguracionCorreoPort
from modules.notificaciones.application.ports.notificacion_repository import (
    NotificacionRepositoryPort,
)
from modules.notificaciones.application.ports.resolutor_destinatarios import (
    ResolutorDestinatariosPort,
)
from modules.notificaciones.application.services.enviar_notificacion import (
    EnviarNotificacionService,
)
from modules.notificaciones.infrastructure.adapters.notificador_registrado import (
    NotificadorRegistrado,
)
from modules.notificaciones.infrastructure.correo.configuracion_correo_adapter import (
    ConfiguracionCorreoSettings,
)
from modules.notificaciones.infrastructure.persistence.mongo.notificacion_repository import (
    MongoNotificacionRepository,
)
from modules.notificaciones.infrastructure.persistence.mongo.resolutor_destinatarios_adapter import (
    MongoResolutorDestinatarios,
)
from shared.application.notifications.ports import NotificadorConAdjuntoPort, NotificadorPort
from shared.infrastructure.notifications.smtp_notificador import SMTPNotificador

# Fabrica del notificador. Vive aparte de las dependencias de la API porque los demas modulos la importan
# para avisar, y las dependencias de la API importan a su vez servicios de otros modulos (los recordatorios):
# juntas formarian un ciclo.


@lru_cache(maxsize=1)
def get_notificacion_repository() -> NotificacionRepositoryPort:
    return MongoNotificacionRepository()


@lru_cache(maxsize=1)
def get_resolutor_destinatarios() -> ResolutorDestinatariosPort:
    return MongoResolutorDestinatarios()


@lru_cache(maxsize=1)
def get_configuracion_correo() -> ConfiguracionCorreoPort:
    return ConfiguracionCorreoSettings()


@lru_cache(maxsize=1)
def get_correo() -> NotificadorConAdjuntoPort:
    return SMTPNotificador()


def get_enviar_notificacion_service() -> EnviarNotificacionService:
    return EnviarNotificacionService(
        notificacion_repository=get_notificacion_repository(),
        resolutor=get_resolutor_destinatarios(),
        configuracion=get_configuracion_correo(),
        correo=get_correo(),
    )


@lru_cache(maxsize=1)
def get_notificador() -> NotificadorPort:
    """El notificador que usan los demas modulos para avisar por correo."""
    return NotificadorRegistrado(get_enviar_notificacion_service())
