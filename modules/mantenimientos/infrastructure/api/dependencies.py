from functools import lru_cache

from modules.mantenimientos.application.ports.activo_resumen_port import ActivoResumenPort
from modules.mantenimientos.application.ports.buscador_activos_port import BuscadorActivosPort
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ResolutorNombresMantenimientoPort,
)
from modules.mantenimientos.application.ports.solicitud_estado_port import SolicitudEstadoPort
from modules.mantenimientos.application.ports.solicitud_verificador_port import (
    SolicitudVerificadorPort,
)
from modules.mantenimientos.application.ports.verificador_tecnico_port import (
    VerificadorTecnicoPort,
)
from modules.mantenimientos.application.services.cambiar_estado_mantenimiento import (
    CambiarEstadoMantenimientoService,
)
from modules.mantenimientos.application.services.crear_mantenimiento import (
    CrearMantenimientoService,
)
from modules.mantenimientos.application.services.eliminar_archivo_mantenimiento import (
    EliminarArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.listar_mantenimientos import (
    ListarMantenimientosService,
)
from modules.mantenimientos.application.services.obtener_archivo_mantenimiento import (
    ObtenerArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.obtener_mantenimiento import (
    ObtenerMantenimientoService,
)
from modules.mantenimientos.application.services.registrar_mantenimientos_masivo import (
    RegistrarMantenimientosMasivoService,
)
from modules.mantenimientos.application.services.subir_archivo_mantenimiento import (
    SubirArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.verificar_alertas_mantenimiento import (
    VerificarAlertasMantenimientoService,
)
from modules.mantenimientos.infrastructure.integracion.solicitud_estado_adapter import (
    SolicitudEstadoAdapter,
)
from modules.mantenimientos.infrastructure.persistence.mongo.activo_resumen_adapter import (
    MongoActivoResumenAdapter,
)
from modules.mantenimientos.infrastructure.persistence.mongo.buscador_activos_adapter import (
    MongoBuscadorActivos,
)
from modules.mantenimientos.infrastructure.persistence.mongo.mantenimiento_repository import (
    MongoMantenimientoRepository,
)
from modules.mantenimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter import (
    MongoResolutorNombresMantenimiento,
)
from modules.mantenimientos.infrastructure.persistence.mongo.solicitud_verificador_adapter import (
    MongoSolicitudVerificador,
)
from modules.mantenimientos.infrastructure.persistence.mongo.verificador_tecnico_adapter import (
    MongoVerificadorTecnico,
)
from shared.application.file_storage.ports import AlmacenArchivosPort
from modules.notificaciones.infrastructure.composicion import get_notificador
from shared.infrastructure.persistence.mongo.almacen_archivos_gridfs import (
    MongoAlmacenArchivosGridFS,
)

_BUCKET_ARCHIVOS = "mantenimientos_archivos"


@lru_cache(maxsize=1)
def get_mantenimiento_repository() -> MantenimientoRepositoryPort:
    return MongoMantenimientoRepository()


@lru_cache(maxsize=1)
def get_activo_resumen_port() -> ActivoResumenPort:
    return MongoActivoResumenAdapter()


@lru_cache(maxsize=1)
def get_verificador_tecnico() -> VerificadorTecnicoPort:
    return MongoVerificadorTecnico()


@lru_cache(maxsize=1)
def get_resolutor_nombres() -> ResolutorNombresMantenimientoPort:
    return MongoResolutorNombresMantenimiento()


@lru_cache(maxsize=1)
def get_solicitud_estado() -> SolicitudEstadoPort:
    return SolicitudEstadoAdapter()


@lru_cache(maxsize=1)
def get_almacen_archivos() -> AlmacenArchivosPort:
    return MongoAlmacenArchivosGridFS(bucket_name=_BUCKET_ARCHIVOS)


@lru_cache(maxsize=1)
def get_solicitud_verificador() -> SolicitudVerificadorPort:
    return MongoSolicitudVerificador()


@lru_cache(maxsize=1)
def get_buscador_activos() -> BuscadorActivosPort:
    return MongoBuscadorActivos()


def get_crear_mantenimiento_service() -> CrearMantenimientoService:
    return CrearMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        activo_resumen_port=get_activo_resumen_port(),
        verificador_tecnico=get_verificador_tecnico(),
        solicitud_verificador=get_solicitud_verificador(),
        notificador=get_notificador(),
    )


def get_registrar_mantenimientos_masivo_service() -> RegistrarMantenimientosMasivoService:
    return RegistrarMantenimientosMasivoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        buscador_activos=get_buscador_activos(),
        verificador_tecnico=get_verificador_tecnico(),
    )


def get_listar_mantenimientos_service() -> ListarMantenimientosService:
    return ListarMantenimientosService(
        mantenimiento_repository=get_mantenimiento_repository(),
        resolutor_nombres=get_resolutor_nombres(),
    )


def get_obtener_mantenimiento_service() -> ObtenerMantenimientoService:
    return ObtenerMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        resolutor_nombres=get_resolutor_nombres(),
    )


def get_cambiar_estado_mantenimiento_service() -> CambiarEstadoMantenimientoService:
    return CambiarEstadoMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        solicitud_estado=get_solicitud_estado(),
    )


def get_subir_archivo_mantenimiento_service() -> SubirArchivoMantenimientoService:
    return SubirArchivoMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        almacen_archivos=get_almacen_archivos(),
    )


def get_obtener_archivo_mantenimiento_service() -> ObtenerArchivoMantenimientoService:
    return ObtenerArchivoMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        almacen_archivos=get_almacen_archivos(),
    )


def get_eliminar_archivo_mantenimiento_service() -> EliminarArchivoMantenimientoService:
    return EliminarArchivoMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        almacen_archivos=get_almacen_archivos(),
    )


def get_verificar_alertas_mantenimiento_service() -> VerificarAlertasMantenimientoService:
    return VerificarAlertasMantenimientoService(
        mantenimiento_repository=get_mantenimiento_repository(),
        activo_resumen_port=get_activo_resumen_port(),
        notificador=get_notificador(),
    )
