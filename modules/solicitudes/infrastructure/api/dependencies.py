from functools import lru_cache

from modules.solicitudes.application.ports.activo_resumen_port import ActivoResumenPort
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.application.services.agregar_seguimiento_solicitud import (
    AgregarSeguimientoSolicitudService,
)
from modules.solicitudes.application.services.cambiar_estado_solicitud import (
    CambiarEstadoSolicitudService,
)
from modules.solicitudes.application.services.crear_solicitud import CrearSolicitudService
from modules.solicitudes.application.services.listar_solicitudes import ListarSolicitudesService
from modules.solicitudes.application.services.obtener_solicitud import ObtenerSolicitudService
from modules.solicitudes.infrastructure.persistence.mongo.activo_resumen_adapter import (
    MongoActivoResumenAdapter,
)
from modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository import (
    MongoSolicitudRepository,
)
from shared.application.notifications.ports import NotificadorPort
from shared.infrastructure.notifications.log_notificador import LogNotificador


@lru_cache(maxsize=1)
def get_solicitud_repository() -> SolicitudRepositoryPort:
    return MongoSolicitudRepository()


@lru_cache(maxsize=1)
def get_activo_resumen_port() -> ActivoResumenPort:
    return MongoActivoResumenAdapter()


@lru_cache(maxsize=1)
def get_notificador() -> NotificadorPort:
    return LogNotificador()


def get_crear_solicitud_service() -> CrearSolicitudService:
    return CrearSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        activo_resumen_port=get_activo_resumen_port(),
        notificador=get_notificador(),
    )


def get_listar_solicitudes_service() -> ListarSolicitudesService:
    return ListarSolicitudesService(solicitud_repository=get_solicitud_repository())


def get_obtener_solicitud_service() -> ObtenerSolicitudService:
    return ObtenerSolicitudService(solicitud_repository=get_solicitud_repository())


def get_cambiar_estado_solicitud_service() -> CambiarEstadoSolicitudService:
    return CambiarEstadoSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        notificador=get_notificador(),
    )


def get_agregar_seguimiento_solicitud_service() -> AgregarSeguimientoSolicitudService:
    return AgregarSeguimientoSolicitudService(solicitud_repository=get_solicitud_repository())
