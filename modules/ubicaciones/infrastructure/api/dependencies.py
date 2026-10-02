from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.movimientos.infrastructure.api.dependencies import get_registrador_de_movimientos
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.infrastructure.api.dependencies import get_producto_repository
from modules.ubicaciones.application.ports.registrador_de_movimientos import (
    RegistradorDeMovimientosPort,
)
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.application.services.actualizar_ubicacion import (
    ActualizarUbicacionService,
)
from modules.ubicaciones.application.services.crear_ubicacion import CrearUbicacionService
from modules.ubicaciones.application.services.eliminar_ubicacion import EliminarUbicacionService
from modules.ubicaciones.application.services.obtener_producto_con_ubicaciones import (
    ObtenerProductoConUbicacionesService,
)
from modules.ubicaciones.application.services.transferir_stock import TransferirStockService
from modules.ubicaciones.infrastructure.persistence.mongo.ubicacion_repository import (
    MongoUbicacionRepository,
)
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.infrastructure.api.dependencies.mongo import get_mongo_db
from shared.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork


def get_ubicacion_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> UbicacionRepositoryPort:
    return MongoUbicacionRepository(db)


def get_unit_of_work_factory() -> UnitOfWorkFactory:
    return lambda: MongoUnitOfWork()


def get_crear_ubicacion_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    registrador_de_movimientos: Annotated[
        RegistradorDeMovimientosPort, Depends(get_registrador_de_movimientos)
    ],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> CrearUbicacionService:
    return CrearUbicacionService(
        ubicacion_repository,
        producto_repository,
        registrador_de_movimientos,
        unit_of_work_factory,
    )


def get_actualizar_ubicacion_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> ActualizarUbicacionService:
    return ActualizarUbicacionService(
        ubicacion_repository, producto_repository, unit_of_work_factory
    )


def get_eliminar_ubicacion_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> EliminarUbicacionService:
    return EliminarUbicacionService(
        ubicacion_repository, producto_repository, unit_of_work_factory
    )


def get_transferir_stock_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    registrador_de_movimientos: Annotated[
        RegistradorDeMovimientosPort, Depends(get_registrador_de_movimientos)
    ],
    unit_of_work_factory: Annotated[UnitOfWorkFactory, Depends(get_unit_of_work_factory)],
) -> TransferirStockService:
    return TransferirStockService(
        ubicacion_repository, registrador_de_movimientos, unit_of_work_factory
    )


def get_obtener_producto_con_ubicaciones_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ObtenerProductoConUbicacionesService:
    return ObtenerProductoConUbicacionesService(ubicacion_repository, producto_repository)
