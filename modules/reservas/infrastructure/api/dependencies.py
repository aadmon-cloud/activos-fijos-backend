from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.application.services.ajustar_reserva import AjustarReservaService
from modules.reservas.application.services.calcular_stock_disponible import (
    CalcularStockDisponibleService,
)
from modules.reservas.application.services.eliminar_reserva import EliminarReservaService
from modules.reservas.application.services.obtener_reserva import ObtenerReservaService
from modules.reservas.infrastructure.persistence.mongo.reserva_repository import (
    MongoReservaRepository,
)
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.infrastructure.api.dependencies import get_ubicacion_repository
from shared.infrastructure.api.dependencies.mongo import get_mongo_db


def get_reserva_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> ReservaRepositoryPort:
    return MongoReservaRepository(db)


def get_calcular_stock_disponible_service(
    ubicacion_repository: Annotated[UbicacionRepositoryPort, Depends(get_ubicacion_repository)],
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
) -> CalcularStockDisponibleService:
    return CalcularStockDisponibleService(ubicacion_repository, reserva_repository)


def get_ajustar_reserva_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
    calcular_stock_disponible_service: Annotated[
        CalcularStockDisponibleService, Depends(get_calcular_stock_disponible_service)
    ],
) -> AjustarReservaService:
    return AjustarReservaService(reserva_repository, calcular_stock_disponible_service)


def get_obtener_reserva_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
) -> ObtenerReservaService:
    return ObtenerReservaService(reserva_repository)


def get_eliminar_reserva_service(
    reserva_repository: Annotated[ReservaRepositoryPort, Depends(get_reserva_repository)],
) -> EliminarReservaService:
    return EliminarReservaService(reserva_repository)
