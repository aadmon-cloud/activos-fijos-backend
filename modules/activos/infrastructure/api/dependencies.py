from functools import lru_cache

from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    MongoActivoRepository,
)
from modules.activos.infrastructure.persistence.mongo.historial_activo_repository import (
    MongoHistorialActivoRepository,
)


@lru_cache(maxsize=1)
def get_activo_repository() -> ActivoRepositoryPort:
    return MongoActivoRepository()


@lru_cache(maxsize=1)
def get_historial_activo_repository() -> HistorialActivoRepositoryPort:
    return MongoHistorialActivoRepository()


def get_crear_activo_service() -> CrearActivoService:
    return CrearActivoService(activo_repository=get_activo_repository())


def get_listar_activos_service() -> ListarActivosService:
    return ListarActivosService(activo_repository=get_activo_repository())


def get_obtener_activo_service() -> ObtenerActivoService:
    return ObtenerActivoService(activo_repository=get_activo_repository())


def get_actualizar_activo_service() -> ActualizarActivoService:
    return ActualizarActivoService(
        activo_repository=get_activo_repository(),
        historial_repository=get_historial_activo_repository(),
    )


def get_cambiar_estado_activo_service() -> CambiarEstadoActivoService:
    return CambiarEstadoActivoService(
        activo_repository=get_activo_repository(),
        historial_repository=get_historial_activo_repository(),
    )


def get_obtener_historial_activo_service() -> ObtenerHistorialActivoService:
    return ObtenerHistorialActivoService(
        activo_repository=get_activo_repository(),
        historial_repository=get_historial_activo_repository(),
    )
