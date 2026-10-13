from functools import lru_cache

from modules.activos.application.services.cambiar_estado_activo import CambiarEstadoActivoService
from modules.activos.infrastructure.persistence.mongo.activo_repository import MongoActivoRepository
from modules.activos.infrastructure.persistence.mongo.historial_activo_repository import (
    MongoHistorialActivoRepository,
)
from modules.solicitudes.application.ports.activo_estado_port import ActivoEstadoPort
from modules.solicitudes.application.ports.activo_resumen_port import ActivoResumenPort
from modules.solicitudes.application.ports.resolutor_referencias import ResolutorReferenciasPort
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
from modules.solicitudes.infrastructure.adapters.activo_estado_adapter import ActivoEstadoAdapter
from modules.solicitudes.infrastructure.persistence.mongo.activo_resumen_adapter import (
    MongoActivoResumenAdapter,
)
from modules.solicitudes.infrastructure.persistence.mongo.resolutor_referencias import (
    MongoResolutorReferencias,
)
from modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository import (
    MongoSolicitudRepository,
)
from modules.notificaciones.infrastructure.composicion import get_notificador


@lru_cache(maxsize=1)
def get_solicitud_repository() -> SolicitudRepositoryPort:
    return MongoSolicitudRepository()


@lru_cache(maxsize=1)
def get_activo_resumen_port() -> ActivoResumenPort:
    return MongoActivoResumenAdapter()


@lru_cache(maxsize=1)
def get_activo_estado_port() -> ActivoEstadoPort:
    activo_repository = MongoActivoRepository()

    return ActivoEstadoAdapter(
        activo_repository=activo_repository,
        cambiar_estado_service=CambiarEstadoActivoService(
            activo_repository=activo_repository,
            historial_repository=MongoHistorialActivoRepository(),
        ),
    )


@lru_cache(maxsize=1)
def get_resolutor_referencias() -> ResolutorReferenciasPort:
    return MongoResolutorReferencias()


def get_crear_solicitud_service() -> CrearSolicitudService:
    return CrearSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        activo_resumen_port=get_activo_resumen_port(),
        notificador=get_notificador(),
    )


def get_listar_solicitudes_service() -> ListarSolicitudesService:
    return ListarSolicitudesService(
        solicitud_repository=get_solicitud_repository(),
        resolutor_referencias=get_resolutor_referencias(),
    )


def get_obtener_solicitud_service() -> ObtenerSolicitudService:
    return ObtenerSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        resolutor_referencias=get_resolutor_referencias(),
    )


def get_cambiar_estado_solicitud_service() -> CambiarEstadoSolicitudService:
    return CambiarEstadoSolicitudService(
        solicitud_repository=get_solicitud_repository(),
        notificador=get_notificador(),
        activo_estado=get_activo_estado_port(),
    )


def get_agregar_seguimiento_solicitud_service() -> AgregarSeguimientoSolicitudService:
    return AgregarSeguimientoSolicitudService(solicitud_repository=get_solicitud_repository())
