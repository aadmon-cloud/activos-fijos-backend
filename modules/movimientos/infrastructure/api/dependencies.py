from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.ports.comprobante import ComprobantePort
from modules.movimientos.application.ports.ejecutor_de_movimientos import (
    EjecutorDeMovimientosPort,
)
from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.storage_repository import StorageRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.confirmar_reserva import ConfirmarReservaService
from modules.movimientos.application.services.confirmar_reserva_kit import (
    ConfirmarReservaKitService,
)
from modules.movimientos.application.services.confirmar_reserva_multiple import (
    ConfirmarReservaMultipleService,
)
from modules.movimientos.application.services.confirmar_reserva_normal import (
    ConfirmarReservaNormalService,
)
from modules.movimientos.application.services.exportar_movimientos_excel import (
    ExportarMovimientosExcelService,
)
from modules.movimientos.application.services.generar_comprobante_pdf import (
    GenerarComprobantePdfService,
)
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.application.services.obtener_pdf_firmado import (
    ObtenerPdfFirmadoService,
)
from modules.movimientos.application.services.registrar_entrada import RegistrarEntradaService
from modules.movimientos.application.services.registrar_entrada_multiple import (
    RegistrarEntradaMultipleService,
)
from modules.movimientos.application.services.registrar_salida import RegistrarSalidaService
from modules.movimientos.application.services.registrar_salida_multiple import (
    RegistrarSalidaMultipleService,
)
from modules.movimientos.application.services.registrar_salida_por_mercado import (
    RegistrarSalidaPorMercadoService,
)
from modules.movimientos.application.services.subir_pdf_firmado import SubirPdfFirmadoService
from modules.movimientos.infrastructure.aprobaciones.ejecutor_de_movimientos_adapter import (
    MovimientosEjecutorAdapter,
)
from modules.movimientos.infrastructure.pdf.reportlab_comprobante import (
    ReportlabComprobanteAdapter,
)
from modules.movimientos.infrastructure.persistence.mongo.generador_secuencial import (
    MongoGeneradorSecuencial,
)
from modules.movimientos.infrastructure.persistence.mongo.movimiento_repository import (
    MongoMovimientoRepository,
)
from modules.movimientos.infrastructure.storage.disk_storage_repository import (
    DiskStorageRepository,
)
from modules.movimientos.infrastructure.ubicaciones.registrador_de_movimientos_adapter import (
    MovimientosRegistradorDeMovimientosAdapter,
)
from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.infrastructure.api.dependencies import (
    get_mercado_predefinido_repository,
)
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.infrastructure.api.dependencies import get_producto_repository
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.infrastructure.persistence.mongo.reserva_repository import (
    MongoReservaRepository,
)
from modules.ubicaciones.application.ports.registrador_de_movimientos import (
    RegistradorDeMovimientosPort,
)
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.infrastructure.persistence.mongo.ubicacion_repository import (
    MongoUbicacionRepository,
)
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.infrastructure.api.dependencies.mongo import get_mongo_db
from shared.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork


def get_movimiento_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> MovimientoRepositoryPort:
    return MongoMovimientoRepository(db)


def get_ubicacion_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> UbicacionRepositoryPort:
    return MongoUbicacionRepository(db)


def get_generador_secuencial(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> GeneradorSecuencialPort:
    return MongoGeneradorSecuencial(db)


def get_reserva_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> ReservaRepositoryPort:
    return MongoReservaRepository(db)


def get_unit_of_work_factory() -> UnitOfWorkFactory:
    return lambda: MongoUnitOfWork()


def get_ajustador_de_stock(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
) -> AjustadorDeStockService:
    return AjustadorDeStockService(producto_repository, ubicacion_repository)


def get_registrador_de_movimientos(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> RegistradorDeMovimientosPort:
    """Adaptador consumido por `ubicaciones` (`CrearUbicacionService`/
    `TransferirStockService`) — expuesto acá porque la implementación
    concreta vive en `movimientos`. Cableado cruzado solo a nivel de
    dependencias (composition root), ver MIGRATION_PLAN.md, incremento 5."""
    return MovimientosRegistradorDeMovimientosAdapter(movimiento_repository, producto_repository)


def get_registrar_entrada_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> RegistrarEntradaService:
    return RegistrarEntradaService(movimiento_repository, ajustador_de_stock, unit_of_work_factory)


def get_registrar_salida_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> RegistrarSalidaService:
    return RegistrarSalidaService(
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def get_registrar_entrada_multiple_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> RegistrarEntradaMultipleService:
    return RegistrarEntradaMultipleService(
        movimiento_repository, ajustador_de_stock, unit_of_work_factory
    )


def get_registrar_salida_multiple_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> RegistrarSalidaMultipleService:
    return RegistrarSalidaMultipleService(
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def get_registrar_salida_por_mercado_service(
    mercado_predefinido_repository: Annotated[
        MercadoPredefinidoRepositoryPort, Depends(get_mercado_predefinido_repository)
    ],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> RegistrarSalidaPorMercadoService:
    return RegistrarSalidaPorMercadoService(
        mercado_predefinido_repository,
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def get_ejecutor_de_movimientos(
    registrar_entrada: Annotated[RegistrarEntradaService, Depends(get_registrar_entrada_service)],
    registrar_entrada_multiple: Annotated[
        RegistrarEntradaMultipleService, Depends(get_registrar_entrada_multiple_service)
    ],
    registrar_salida: Annotated[RegistrarSalidaService, Depends(get_registrar_salida_service)],
    registrar_salida_multiple: Annotated[
        RegistrarSalidaMultipleService, Depends(get_registrar_salida_multiple_service)
    ],
) -> EjecutorDeMovimientosPort:
    """Consumido por `aprobaciones_pendientes` al confirmar una propuesta —
    expuesto acá porque la implementación concreta vive en `movimientos`.
    Mismo patrón de cableado cruzado ya usado para `get_registrador_de_movimientos`."""
    return MovimientosEjecutorAdapter(
        registrar_entrada,
        registrar_entrada_multiple,
        registrar_salida,
        registrar_salida_multiple,
    )


def get_comprobante_port() -> ComprobantePort:
    return ReportlabComprobanteAdapter()


def get_storage_repository() -> StorageRepositoryPort:
    return DiskStorageRepository()


def _get_confirmar_reserva_normal_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> ConfirmarReservaNormalService:
    return ConfirmarReservaNormalService(
        reserva_repository,
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def _get_confirmar_reserva_kit_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> ConfirmarReservaKitService:
    return ConfirmarReservaKitService(
        reserva_repository,
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def _get_confirmar_reserva_multiple_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    ajustador_de_stock: Annotated[AjustadorDeStockService, Depends(get_ajustador_de_stock)],
    generador_secuencial: Annotated[GeneradorSecuencialPort, Depends(get_generador_secuencial)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> ConfirmarReservaMultipleService:
    return ConfirmarReservaMultipleService(
        reserva_repository,
        movimiento_repository,
        ajustador_de_stock,
        generador_secuencial,
        unit_of_work_factory,
    )


def get_confirmar_reserva_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
    confirmar_normal_service: Annotated[
        ConfirmarReservaNormalService, Depends(_get_confirmar_reserva_normal_service)
    ],
    confirmar_kit_service: Annotated[
        ConfirmarReservaKitService, Depends(_get_confirmar_reserva_kit_service)
    ],
    confirmar_multiple_service: Annotated[
        ConfirmarReservaMultipleService, Depends(_get_confirmar_reserva_multiple_service)
    ],
) -> ConfirmarReservaService:
    return ConfirmarReservaService(
        reserva_repository,
        confirmar_normal_service,
        confirmar_kit_service,
        confirmar_multiple_service,
    )


def get_generar_comprobante_pdf_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    comprobante_port: Annotated[ComprobantePort, Depends(get_comprobante_port)],
) -> GenerarComprobantePdfService:
    return GenerarComprobantePdfService(movimiento_repository, comprobante_port)


def get_subir_pdf_firmado_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    storage_repository: Annotated[StorageRepositoryPort, Depends(get_storage_repository)],
) -> SubirPdfFirmadoService:
    return SubirPdfFirmadoService(movimiento_repository, storage_repository)


def get_obtener_pdf_firmado_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
    storage_repository: Annotated[StorageRepositoryPort, Depends(get_storage_repository)],
) -> ObtenerPdfFirmadoService:
    return ObtenerPdfFirmadoService(movimiento_repository, storage_repository)


def get_listar_movimientos_input(
    producto_codigo: str | None = None,
    tipo: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    motivo: str | None = None,
    remision: str | None = None,
    caso: str | None = None,
    origen_destino: str | None = None,
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=200),
) -> ListarMovimientosInput:
    return ListarMovimientosInput(
        producto_codigo=producto_codigo,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        motivo=motivo,
        remision=remision,
        caso=caso,
        origen_destino=origen_destino,
        pagina=pagina,
        limite=limite,
    )


def get_listar_movimientos_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
) -> ListarMovimientosService:
    return ListarMovimientosService(movimiento_repository)


def get_exportar_movimientos_excel_input(
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    tipo: str | None = None,
) -> ExportarMovimientosExcelInput:
    return ExportarMovimientosExcelInput(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, tipo=tipo
    )


def get_exportar_movimientos_excel_service(
    movimiento_repository: Annotated[MovimientoRepositoryPort, Depends(get_movimiento_repository)],
) -> ExportarMovimientosExcelService:
    return ExportarMovimientosExcelService(movimiento_repository)
