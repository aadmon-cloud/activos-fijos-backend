from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.application.services.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoService,
)
from modules.mercados_predefinidos.application.services.crear_mercado_predefinido import (
    CrearMercadoPredefinidoService,
)
from modules.mercados_predefinidos.application.services.listar_mercados_predefinidos import (
    ListarMercadosPredefinidosService,
)
from modules.mercados_predefinidos.application.services.obtener_mercado_predefinido import (
    ObtenerMercadoPredefinidoService,
)
from modules.mercados_predefinidos.infrastructure.persistence.mongo.mercado_predefinido_repository import (
    MongoMercadoPredefinidoRepository,
)
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.infrastructure.api.dependencies import get_producto_repository
from shared.infrastructure.api.dependencies.mongo import get_mongo_db


def get_mercado_predefinido_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> MercadoPredefinidoRepositoryPort:
    return MongoMercadoPredefinidoRepository(db)


def get_crear_mercado_predefinido_service(
    mercado_repository: Annotated[
        MercadoPredefinidoRepositoryPort, Depends(get_mercado_predefinido_repository)
    ],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> CrearMercadoPredefinidoService:
    return CrearMercadoPredefinidoService(mercado_repository, producto_repository)


def get_actualizar_mercado_predefinido_service(
    mercado_repository: Annotated[
        MercadoPredefinidoRepositoryPort, Depends(get_mercado_predefinido_repository)
    ],
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ActualizarMercadoPredefinidoService:
    return ActualizarMercadoPredefinidoService(mercado_repository, producto_repository)


def get_listar_mercados_predefinidos_service(
    mercado_repository: Annotated[
        MercadoPredefinidoRepositoryPort, Depends(get_mercado_predefinido_repository)
    ],
) -> ListarMercadosPredefinidosService:
    return ListarMercadosPredefinidosService(mercado_repository)


def get_obtener_mercado_predefinido_service(
    mercado_repository: Annotated[
        MercadoPredefinidoRepositoryPort, Depends(get_mercado_predefinido_repository)
    ],
) -> ObtenerMercadoPredefinidoService:
    return ObtenerMercadoPredefinidoService(mercado_repository)
