from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from modules.auth.domain.entities.usuario import Usuario
from modules.reservas.application.dto.ajuste_item import AjusteItemInput
from modules.reservas.application.dto.ajustar_reserva import AjustarReservaInput
from modules.reservas.application.services.ajustar_reserva import AjustarReservaService
from modules.reservas.application.services.calcular_stock_disponible import (
    CalcularStockDisponibleService,
)
from modules.reservas.application.services.eliminar_reserva import EliminarReservaService
from modules.reservas.application.services.obtener_reserva import ObtenerReservaService
from modules.reservas.domain.entities.reserva import Reserva
from modules.reservas.infrastructure.api.dependencies import (
    get_ajustar_reserva_service,
    get_calcular_stock_disponible_service,
    get_eliminar_reserva_service,
    get_obtener_reserva_service,
)
from modules.reservas.infrastructure.api.schemas import (
    AjustarReservaRequest,
    MessageResponse,
    ReservaResponse,
    StockDisponibleResponse,
)
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import (
    require_authenticated,
    require_super_admin,
)

router = APIRouter(prefix="/api/reservas", tags=["reservas"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


def _reserva_response(reserva: Reserva) -> ReservaResponse:
    return ReservaResponse.model_validate(reserva.model_dump())


@router.get(
    "/stock-disponible/{producto_codigo}/{ubicacion}",
    response_model=StockDisponibleResponse,
    summary="Calcula el stock disponible de un producto en una ubicación, considerando reservas activas",
    responses={404: {"description": "No existe esa ubicación para ese producto"}},
)
async def calcular_stock_disponible(
    producto_codigo: str,
    ubicacion: str,
    service: Annotated[
        CalcularStockDisponibleService, Depends(get_calcular_stock_disponible_service)
    ],
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    session_id: str | None = Query(default=None),
) -> StockDisponibleResponse:
    resultado = await service.ejecutar(producto_codigo, ubicacion, session_id)
    return StockDisponibleResponse.model_validate(resultado.model_dump())


@router.get(
    "/{session_id}",
    response_model=ReservaResponse,
    summary="Obtiene la reserva (carrito) de una sesión",
    responses={404: {"description": "No existe una reserva para esa sesión"}},
)
async def obtener_reserva(
    session_id: str,
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ObtenerReservaService, Depends(get_obtener_reserva_service)],
) -> ReservaResponse:
    reserva = await service.ejecutar(session_id)
    return _reserva_response(reserva)


@router.post(
    "/{session_id}/ajustar",
    summary="Agrega o quita cantidad de items en la reserva de una sesión",
    responses={
        400: {"description": "Stock disponible insuficiente para el ajuste solicitado"},
        404: {"description": "No existe la ubicación referenciada por algún ajuste"},
    },
)
async def ajustar_reserva(
    session_id: str,
    payload: AjustarReservaRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[AjustarReservaService, Depends(get_ajustar_reserva_service)],
) -> ReservaResponse | MessageResponse:
    reserva = await service.ejecutar(
        session_id,
        AjustarReservaInput(
            ajustes=[
                AjusteItemInput(
                    producto_codigo=a.producto_codigo,
                    ubicacion=a.ubicacion,
                    diferencia=a.diferencia,
                )
                for a in payload.ajustes
            ],
            datos_adicionales=payload.datos_adicionales,
        ),
        _audit_persona(usuario_actual),
    )
    if reserva is None:
        return MessageResponse(message="La reserva quedó sin items y se eliminó.")
    return _reserva_response(reserva)


@router.delete(
    "/{session_id}",
    response_model=MessageResponse,
    summary="Elimina la reserva de una sesión (solo super_admin)",
    responses={404: {"description": "No existe una reserva para esa sesión"}},
)
async def eliminar_reserva(
    session_id: str,
    _usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[EliminarReservaService, Depends(get_eliminar_reserva_service)],
) -> MessageResponse:
    await service.ejecutar(session_id)
    return MessageResponse(message="Reserva eliminada exitosamente.")
