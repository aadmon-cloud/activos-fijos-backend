from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from modules.auth.domain.entities.usuario import Usuario
from modules.productos.application.dto.actualizar_producto import ActualizarProductoInput
from modules.productos.application.dto.crear_producto import CrearProductoInput
from modules.productos.application.dto.listar_productos import ListarProductosInput
from modules.productos.application.services.actualizar_producto import (
    ActualizarProductoService,
)
from modules.productos.application.services.buscar_productos import BuscarProductosService
from modules.productos.application.services.crear_producto import CrearProductoService
from modules.productos.application.services.eliminar_producto import EliminarProductoService
from modules.productos.application.services.listar_productos import ListarProductosService
from modules.productos.application.services.obtener_producto import ObtenerProductoService
from modules.productos.infrastructure.api.dependencies import (
    get_actualizar_producto_service,
    get_buscar_productos_service,
    get_crear_producto_service,
    get_eliminar_producto_service,
    get_listar_productos_input,
    get_listar_productos_service,
    get_obtener_producto_service,
)
from modules.productos.infrastructure.api.schemas import (
    ActualizarProductoRequest,
    CrearProductoRequest,
    MessageResponse,
    ProductoResponse,
    ProductosPaginadosResponse,
)
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import require_authenticated

router = APIRouter(prefix="/api/productos", tags=["productos"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


@router.get(
    "",
    response_model=ProductosPaginadosResponse,
    summary="Lista productos paginados",
)
async def listar_productos(
    entrada: Annotated[ListarProductosInput, Depends(get_listar_productos_input)],
    service: Annotated[ListarProductosService, Depends(get_listar_productos_service)],
) -> ProductosPaginadosResponse:
    resultado = await service.ejecutar(entrada)
    return ProductosPaginadosResponse(
        resultado=[
            ProductoResponse.model_validate(producto.model_dump())
            for producto in resultado.resultado
        ],
        pagina_actual=resultado.pagina_actual,
        elementos_por_pagina=resultado.elementos_por_pagina,
        total_elementos=resultado.total_elementos,
        total_paginas=resultado.total_paginas,
    )


@router.get(
    "/buscar",
    response_model=list[ProductoResponse],
    summary="Busca productos por nombre, código o descripción",
)
async def buscar_productos(
    q: Annotated[str, Query(min_length=1, description="Término de búsqueda")],
    service: Annotated[BuscarProductosService, Depends(get_buscar_productos_service)],
) -> list[ProductoResponse]:
    productos = await service.ejecutar(q)
    return [ProductoResponse.model_validate(producto.model_dump()) for producto in productos]


@router.get(
    "/{codigo}",
    response_model=ProductoResponse,
    summary="Obtiene un producto por su código",
    responses={404: {"description": "No existe un producto con ese código"}},
)
async def obtener_producto(
    codigo: str,
    service: Annotated[ObtenerProductoService, Depends(get_obtener_producto_service)],
) -> ProductoResponse:
    producto = await service.ejecutar(codigo)
    return ProductoResponse.model_validate(producto.model_dump())


@router.post(
    "",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuevo producto",
    responses={409: {"description": "El código ya está registrado"}},
)
async def crear_producto(
    payload: CrearProductoRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[CrearProductoService, Depends(get_crear_producto_service)],
) -> ProductoResponse:
    producto = await service.ejecutar(
        CrearProductoInput(
            codigo=payload.codigo,
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            categoria=payload.categoria,
            stock_minimo=payload.stock_minimo,
            precio_unitario=payload.precio_unitario,
        ),
        _audit_persona(usuario_actual),
    )
    return ProductoResponse.model_validate(producto.model_dump())


@router.put(
    "/{codigo}",
    response_model=ProductoResponse,
    summary="Actualiza un producto existente",
    responses={404: {"description": "No existe un producto con ese código"}},
)
async def actualizar_producto(
    codigo: str,
    payload: ActualizarProductoRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ActualizarProductoService, Depends(get_actualizar_producto_service)],
) -> ProductoResponse:
    producto = await service.ejecutar(
        codigo,
        ActualizarProductoInput(
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            categoria=payload.categoria,
            stock_minimo=payload.stock_minimo,
            precio_unitario=payload.precio_unitario,
        ),
        _audit_persona(usuario_actual),
    )
    return ProductoResponse.model_validate(producto.model_dump())


@router.delete(
    "/{codigo}",
    response_model=MessageResponse,
    summary="Elimina un producto",
    responses={404: {"description": "No existe un producto con ese código"}},
)
async def eliminar_producto(
    codigo: str,
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[EliminarProductoService, Depends(get_eliminar_producto_service)],
) -> MessageResponse:
    await service.ejecutar(codigo)
    return MessageResponse(message="Producto eliminado exitosamente.")
