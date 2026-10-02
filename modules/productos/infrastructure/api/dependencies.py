from typing import Annotated

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.productos.application.dto.listar_productos import ListarProductosInput
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.application.services.actualizar_producto import (
    ActualizarProductoService,
)
from modules.productos.application.services.buscar_productos import BuscarProductosService
from modules.productos.application.services.crear_producto import CrearProductoService
from modules.productos.application.services.eliminar_producto import EliminarProductoService
from modules.productos.application.services.listar_productos import ListarProductosService
from modules.productos.application.services.obtener_producto import ObtenerProductoService
from modules.productos.infrastructure.persistence.mongo.producto_repository import (
    MongoProductoRepository,
)
from shared.infrastructure.api.dependencies.mongo import get_mongo_db


def get_producto_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> ProductoRepositoryPort:
    return MongoProductoRepository(db)


def get_crear_producto_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> CrearProductoService:
    return CrearProductoService(producto_repository)


def get_actualizar_producto_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ActualizarProductoService:
    return ActualizarProductoService(producto_repository)


def get_eliminar_producto_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> EliminarProductoService:
    return EliminarProductoService(producto_repository)


def get_obtener_producto_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ObtenerProductoService:
    return ObtenerProductoService(producto_repository)


def get_listar_productos_input(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=10, ge=1, le=100),
) -> ListarProductosInput:
    return ListarProductosInput(pagina=pagina, limite=limite)


def get_listar_productos_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> ListarProductosService:
    return ListarProductosService(producto_repository)


def get_buscar_productos_service(
    producto_repository: Annotated[ProductoRepositoryPort, Depends(get_producto_repository)],
) -> BuscarProductosService:
    return BuscarProductosService(producto_repository)
