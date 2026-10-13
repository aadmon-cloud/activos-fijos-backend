from functools import lru_cache

from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.generador_comprobante_port import (
    GeneradorComprobantePort,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.application.ports.verificador_usuario_port import VerificadorUsuarioPort
from modules.movimientos.application.services.aprobar_movimiento import AprobarMovimientoService
from modules.movimientos.application.services.confirmar_devolucion_movimiento import (
    ConfirmarDevolucionMovimientoService,
)
from modules.movimientos.application.services.confirmar_salida_movimiento import (
    ConfirmarSalidaMovimientoService,
)
from modules.movimientos.application.services.ejecutar_baja_movimiento import (
    EjecutarBajaMovimientoService,
)
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.application.services.obtener_comprobante_movimiento import (
    ObtenerComprobanteMovimientoService,
)
from modules.movimientos.application.services.obtener_movimiento import ObtenerMovimientoService
from modules.movimientos.application.services.recordar_devoluciones_movimiento import (
    RecordarDevolucionesMovimientoService,
)
from modules.movimientos.application.services.rechazar_movimiento import RechazarMovimientoService
from modules.movimientos.application.services.solicitar_devolucion_movimiento import (
    SolicitarDevolucionMovimientoService,
)
from modules.movimientos.application.services.solicitar_movimiento import (
    SolicitarMovimientoService,
)
from modules.movimientos.infrastructure.persistence.mongo.activo_movimiento_adapter import (
    MongoActivoMovimientoAdapter,
)
from modules.movimientos.infrastructure.persistence.mongo.movimiento_repository import (
    MongoMovimientoRepository,
)
from modules.movimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter import (
    MongoResolutorNombresMovimiento,
)
from modules.movimientos.infrastructure.persistence.mongo.verificador_usuario_adapter import (
    MongoVerificadorUsuario,
)
from modules.movimientos.infrastructure.reportes.generador_comprobante_pdf import (
    GeneradorComprobantePdf,
)
from modules.notificaciones.infrastructure.composicion import get_notificador
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.infrastructure.persistence.mongo.almacen_archivos_gridfs import (
    MongoAlmacenArchivosGridFS,
)

_BUCKET_ARCHIVOS = "movimientos_archivos"


@lru_cache(maxsize=1)
def get_movimiento_repository() -> MovimientoRepositoryPort:
    return MongoMovimientoRepository()


@lru_cache(maxsize=1)
def get_activo_movimiento() -> ActivoMovimientoPort:
    return MongoActivoMovimientoAdapter()


@lru_cache(maxsize=1)
def get_verificador_usuario() -> VerificadorUsuarioPort:
    return MongoVerificadorUsuario()


@lru_cache(maxsize=1)
def get_resolutor_nombres() -> ResolutorNombresMovimientoPort:
    return MongoResolutorNombresMovimiento()


@lru_cache(maxsize=1)
def get_generador_comprobante() -> GeneradorComprobantePort:
    return GeneradorComprobantePdf()


@lru_cache(maxsize=1)
def get_almacen_archivos() -> AlmacenArchivosPort:
    return MongoAlmacenArchivosGridFS(bucket_name=_BUCKET_ARCHIVOS)


def get_solicitar_movimiento_service() -> SolicitarMovimientoService:
    return SolicitarMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        verificador_usuario=get_verificador_usuario(),
        notificador=get_notificador(),
    )


def get_aprobar_movimiento_service() -> AprobarMovimientoService:
    return AprobarMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_rechazar_movimiento_service() -> RechazarMovimientoService:
    return RechazarMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_confirmar_salida_movimiento_service() -> ConfirmarSalidaMovimientoService:
    return ConfirmarSalidaMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        resolutor_nombres=get_resolutor_nombres(),
        generador_comprobante=get_generador_comprobante(),
        almacen_archivos=get_almacen_archivos(),
        notificador=get_notificador(),
    )


def get_solicitar_devolucion_movimiento_service() -> SolicitarDevolucionMovimientoService:
    return SolicitarDevolucionMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_confirmar_devolucion_movimiento_service() -> ConfirmarDevolucionMovimientoService:
    return ConfirmarDevolucionMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_ejecutar_baja_movimiento_service() -> EjecutarBajaMovimientoService:
    return EjecutarBajaMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_recordar_devoluciones_movimiento_service() -> RecordarDevolucionesMovimientoService:
    return RecordarDevolucionesMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        activo_movimiento=get_activo_movimiento(),
        notificador=get_notificador(),
    )


def get_obtener_movimiento_service() -> ObtenerMovimientoService:
    return ObtenerMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        resolutor_nombres=get_resolutor_nombres(),
        activo_movimiento=get_activo_movimiento(),
    )


def get_listar_movimientos_service() -> ListarMovimientosService:
    return ListarMovimientosService(
        movimiento_repository=get_movimiento_repository(),
        resolutor_nombres=get_resolutor_nombres(),
        activo_movimiento=get_activo_movimiento(),
    )


def get_obtener_comprobante_movimiento_service() -> ObtenerComprobanteMovimientoService:
    return ObtenerComprobanteMovimientoService(
        movimiento_repository=get_movimiento_repository(),
        almacen_archivos=get_almacen_archivos(),
        activo_movimiento=get_activo_movimiento(),
    )
