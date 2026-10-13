from functools import lru_cache

from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort
from modules.activos.application.ports.resolutor_nombres import ResolutorNombresPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.application.services.eliminar_foto_activo import EliminarFotoActivoService
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.application.services.obtener_foto_activo import ObtenerFotoActivoService
from modules.activos.application.services.subir_foto_activo import SubirFotoActivoService
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    MongoActivoRepository,
)
from modules.activos.infrastructure.persistence.mongo.almacen_fotos import MongoAlmacenFotos
from modules.activos.infrastructure.persistence.mongo.resolutor_nombres import (
    MongoResolutorNombres,
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


@lru_cache(maxsize=1)
def get_resolutor_nombres() -> ResolutorNombresPort:
    return MongoResolutorNombres()


def get_crear_activo_service() -> CrearActivoService:
    return CrearActivoService(activo_repository=get_activo_repository())


def get_listar_activos_service() -> ListarActivosService:
    return ListarActivosService(
        activo_repository=get_activo_repository(),
        resolutor_nombres=get_resolutor_nombres(),
    )


def get_obtener_activo_service() -> ObtenerActivoService:
    return ObtenerActivoService(
        activo_repository=get_activo_repository(),
        resolutor_nombres=get_resolutor_nombres(),
    )


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
        resolutor_nombres=get_resolutor_nombres(),
    )


@lru_cache(maxsize=1)
def get_almacen_fotos() -> AlmacenFotosPort:
    return MongoAlmacenFotos()


def get_subir_foto_activo_service() -> SubirFotoActivoService:
    return SubirFotoActivoService(
        activo_repository=get_activo_repository(), almacen_fotos=get_almacen_fotos()
    )


def get_obtener_foto_activo_service() -> ObtenerFotoActivoService:
    return ObtenerFotoActivoService(almacen_fotos=get_almacen_fotos())


def get_eliminar_foto_activo_service() -> EliminarFotoActivoService:
    return EliminarFotoActivoService(
        activo_repository=get_activo_repository(), almacen_fotos=get_almacen_fotos()
    )
