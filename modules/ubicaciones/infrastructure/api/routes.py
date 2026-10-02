from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.auth.domain.entities.usuario import Usuario
from modules.ubicaciones.application.dto.actualizar_ubicacion import ActualizarUbicacionInput
from modules.ubicaciones.application.dto.crear_ubicacion import CrearUbicacionInput
from modules.ubicaciones.application.dto.transferir_stock import TransferirStockInput
from modules.ubicaciones.application.services.actualizar_ubicacion import (
    ActualizarUbicacionService,
)
from modules.ubicaciones.application.services.crear_ubicacion import CrearUbicacionService
from modules.ubicaciones.application.services.eliminar_ubicacion import EliminarUbicacionService
from modules.ubicaciones.application.services.obtener_producto_con_ubicaciones import (
    ObtenerProductoConUbicacionesService,
)
from modules.ubicaciones.application.services.transferir_stock import TransferirStockService
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.infrastructure.api.dependencies import (
    get_actualizar_ubicacion_service,
    get_crear_ubicacion_service,
    get_eliminar_ubicacion_service,
    get_obtener_producto_con_ubicaciones_service,
    get_transferir_stock_service,
)
from modules.ubicaciones.infrastructure.api.schemas import (
    ActualizarUbicacionRequest,
    CrearUbicacionRequest,
    MessageResponse,
    ProductoConUbicacionesResponse,
    TransferirStockRequest,
    UbicacionResponse,
)
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import require_authenticated

router = APIRouter(prefix="/api/productos", tags=["ubicaciones"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


def _ubicacion_response(ubicacion: Ubicacion) -> UbicacionResponse:
    return UbicacionResponse(
        id=ubicacion.id,
        producto_codigo=ubicacion.producto_codigo,
        ubicacion=ubicacion.ubicacion,
        stock_fisico=ubicacion.stock_fisico,
        stock_reservado=ubicacion.stock_reservado,
        stock_disponible=ubicacion.stock_disponible,
    )


@router.get(
    "/{codigo}/ubicaciones",
    response_model=ProductoConUbicacionesResponse,
    summary="Obtiene un producto junto con sus ubicaciones físicas",
    responses={404: {"description": "No existe un producto con ese código"}},
)
async def obtener_producto_con_ubicaciones(
    codigo: str,
    service: Annotated[
        ObtenerProductoConUbicacionesService,
        Depends(get_obtener_producto_con_ubicaciones_service),
    ],
) -> ProductoConUbicacionesResponse:
    producto, ubicaciones = await service.ejecutar(codigo)
    respuestas = [_ubicacion_response(u) for u in ubicaciones]
    return ProductoConUbicacionesResponse(
        producto=producto.model_dump(),
        ubicaciones=respuestas,
        total_ubicaciones=len(respuestas),
    )


@router.post(
    "/{codigo}/ubicaciones",
    response_model=UbicacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva ubicación física para un producto",
    responses={
        404: {"description": "No existe un producto con ese código"},
        409: {"description": "El producto ya tiene una ubicación con ese nombre"},
    },
)
async def crear_ubicacion(
    codigo: str,
    payload: CrearUbicacionRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[CrearUbicacionService, Depends(get_crear_ubicacion_service)],
) -> UbicacionResponse:
    ubicacion = await service.ejecutar(
        CrearUbicacionInput(
            producto_codigo=codigo, ubicacion=payload.ubicacion, cantidad=payload.cantidad
        ),
        _audit_persona(usuario_actual),
    )
    return _ubicacion_response(ubicacion)


@router.post(
    "/{codigo}/ubicaciones/transferir",
    response_model=MessageResponse,
    summary="Transfiere stock entre dos ubicaciones del mismo producto",
    responses={
        404: {"description": "No existe la ubicación de origen"},
        400: {"description": "Stock insuficiente en la ubicación de origen"},
    },
)
async def transferir_stock(
    codigo: str,
    payload: TransferirStockRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[TransferirStockService, Depends(get_transferir_stock_service)],
) -> MessageResponse:
    await service.ejecutar(
        codigo,
        TransferirStockInput(
            origen=payload.origen, destino=payload.destino, cantidad=payload.cantidad
        ),
        _audit_persona(usuario_actual),
    )
    return MessageResponse(
        message=f"Transferidas {payload.cantidad} unidades de '{payload.origen}' a '{payload.destino}'."
    )


@router.put(
    "/{codigo}/ubicaciones/{ubicacion}",
    response_model=UbicacionResponse,
    summary="Actualiza el stock físico de una ubicación",
    responses={404: {"description": "No existe esa ubicación para el producto"}},
)
async def actualizar_ubicacion(
    codigo: str,
    ubicacion: str,
    payload: ActualizarUbicacionRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ActualizarUbicacionService, Depends(get_actualizar_ubicacion_service)],
) -> UbicacionResponse:
    resultado = await service.ejecutar(
        codigo,
        ubicacion,
        ActualizarUbicacionInput(cantidad=payload.cantidad),
        _audit_persona(usuario_actual),
    )
    return _ubicacion_response(resultado)


@router.delete(
    "/{codigo}/ubicaciones/{ubicacion}",
    response_model=MessageResponse,
    summary="Elimina una ubicación de un producto",
    responses={404: {"description": "No existe esa ubicación para el producto"}},
)
async def eliminar_ubicacion(
    codigo: str,
    ubicacion: str,
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[EliminarUbicacionService, Depends(get_eliminar_ubicacion_service)],
) -> MessageResponse:
    await service.ejecutar(codigo, ubicacion)
    return MessageResponse(message="Ubicación eliminada exitosamente.")
