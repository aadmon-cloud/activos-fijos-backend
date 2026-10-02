from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.application.services.confirmar_movimiento_pendiente import (
    ConfirmarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.application.services.eliminar_movimiento_pendiente import (
    EliminarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.application.services.eliminar_movimientos_pendientes_multiples import (
    EliminarMovimientosPendientesMultiplesService,
)
from modules.aprobaciones_pendientes.application.services.listar_movimientos_pendientes import (
    ListarMovimientosPendientesService,
)
from modules.aprobaciones_pendientes.application.services.proponer_entrada import (
    ProponerEntradaService,
)
from modules.aprobaciones_pendientes.application.services.proponer_entrada_multiple import (
    ProponerEntradaMultipleService,
)
from modules.aprobaciones_pendientes.application.services.proponer_salida import (
    ProponerSalidaService,
)
from modules.aprobaciones_pendientes.application.services.proponer_salida_multiple import (
    ProponerSalidaMultipleService,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.infrastructure.api.dependencies import (
    get_confirmar_movimiento_pendiente_service,
    get_eliminar_movimiento_pendiente_service,
    get_eliminar_movimientos_pendientes_multiples_service,
    get_listar_movimientos_pendientes_input,
    get_listar_movimientos_pendientes_service,
    get_proponer_entrada_multiple_service,
    get_proponer_entrada_service,
    get_proponer_salida_multiple_service,
    get_proponer_salida_service,
)
from modules.aprobaciones_pendientes.infrastructure.api.schemas import (
    EliminarMovimientosPendientesMultiplesRequest,
    EliminarMovimientosPendientesMultiplesResponse,
    MovimientoPendienteResponse,
    MovimientosPendientesPaginadosResponse,
    ProponerEntradaMultipleRequest,
    ProponerEntradaRequest,
    ProponerSalidaMultipleRequest,
    ProponerSalidaRequest,
)
from modules.auth.domain.entities.usuario import RolUsuario, Usuario
from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    ItemSalidaMultipleInput,
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.infrastructure.api.schemas import (
    ItemMovimientoResponse,
    MovimientoResponse,
)
from shared.domain.entities.audit_persona import AuditPersona
from shared.infrastructure.api.dependencies.auth import require_authenticated, require_super_admin

router = APIRouter(prefix="/api/aprobaciones-pendientes", tags=["aprobaciones-pendientes"])


def _audit_persona(usuario: Usuario) -> AuditPersona:
    return AuditPersona(id_persona=usuario.id, nombre=usuario.username, fecha=datetime.now(UTC))


def _es_super_admin(usuario: Usuario) -> bool:
    return usuario.rol == RolUsuario.SUPER_ADMIN


def _movimiento_pendiente_response(pendiente: MovimientoPendiente) -> MovimientoPendienteResponse:
    return MovimientoPendienteResponse(
        id=pendiente.id,
        tipo_propuesto=pendiente.tipo_propuesto,
        payload=pendiente.payload,
        estado=pendiente.estado,
        movimiento_id=pendiente.movimiento_id,
        propuesto_por=pendiente.creado_por.nombre,
        fecha_propuesta=pendiente.creado_por.fecha,
        confirmado_por=pendiente.confirmado_por.nombre if pendiente.confirmado_por else None,
        fecha_confirmacion=pendiente.confirmado_por.fecha if pendiente.confirmado_por else None,
    )


def _movimiento_response(movimiento) -> MovimientoResponse:
    return MovimientoResponse(
        id=movimiento.id,
        tipo=movimiento.tipo,
        modalidad=movimiento.modalidad,
        producto_codigo=movimiento.producto_codigo,
        producto_nombre=movimiento.producto_nombre,
        cantidad=movimiento.cantidad,
        motivo=movimiento.motivo,
        tipo_origen=movimiento.tipo_origen,
        origen_nombre=movimiento.origen_nombre,
        cliente_destino=movimiento.cliente_destino,
        ubicacion=movimiento.ubicacion,
        ubicacion_origen=movimiento.ubicacion_origen,
        ubicacion_destino=movimiento.ubicacion_destino,
        notas=movimiento.notas,
        remision=movimiento.remision,
        caso=movimiento.caso,
        referencia=movimiento.referencia,
        numero_cajas=movimiento.numero_cajas,
        kit_nombre=movimiento.kit_nombre,
        nombre_mercado=movimiento.nombre_mercado,
        productos=(
            [ItemMovimientoResponse(**item.model_dump()) for item in movimiento.productos]
            if movimiento.productos
            else None
        ),
        pdf_nombre=movimiento.pdf_nombre,
        usuario=movimiento.creado_por.nombre,
        fecha=movimiento.creado_por.fecha,
    )


@router.post(
    "/entradas",
    response_model=MovimientoPendienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propone una entrada individual, pendiente de confirmación (requiere super_admin)",
)
async def proponer_entrada(
    payload: ProponerEntradaRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ProponerEntradaService, Depends(get_proponer_entrada_service)],
) -> MovimientoPendienteResponse:
    pendiente = await service.ejecutar(
        RegistrarEntradaInput(
            producto_codigo=payload.producto_codigo,
            cantidad=payload.cantidad,
            motivo=payload.motivo,
            tipo_origen=payload.tipo_origen,
            origen_nombre=payload.origen_nombre,
            ubicacion=payload.ubicacion,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_pendiente_response(pendiente)


@router.post(
    "/entradas/multiple",
    response_model=MovimientoPendienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propone una entrada con varios productos, pendiente de confirmación",
    responses={422: {"description": "tipo_origen fuera del vocabulario válido, o productos vacío"}},
)
async def proponer_entrada_multiple(
    payload: ProponerEntradaMultipleRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ProponerEntradaMultipleService, Depends(get_proponer_entrada_multiple_service)
    ],
) -> MovimientoPendienteResponse:
    pendiente = await service.ejecutar(
        RegistrarEntradaMultipleInput(
            productos=[
                ItemEntradaMultipleInput(
                    producto_codigo=item.producto_codigo,
                    cantidad=item.cantidad,
                    ubicacion=item.ubicacion,
                )
                for item in payload.productos
            ],
            tipo_origen=payload.tipo_origen,
            origen_nombre=payload.origen_nombre,
            ubicacion=payload.ubicacion,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_pendiente_response(pendiente)


@router.post(
    "/salidas",
    response_model=MovimientoPendienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propone una salida individual, pendiente de confirmación",
)
async def proponer_salida(
    payload: ProponerSalidaRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[ProponerSalidaService, Depends(get_proponer_salida_service)],
) -> MovimientoPendienteResponse:
    pendiente = await service.ejecutar(
        RegistrarSalidaInput(
            producto_codigo=payload.producto_codigo,
            cantidad=payload.cantidad,
            ubicacion=payload.ubicacion,
            motivo=payload.motivo,
            cliente_destino=payload.cliente_destino,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_pendiente_response(pendiente)


@router.post(
    "/salidas/multiple",
    response_model=MovimientoPendienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propone una salida con varios productos, pendiente de confirmación",
)
async def proponer_salida_multiple(
    payload: ProponerSalidaMultipleRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ProponerSalidaMultipleService, Depends(get_proponer_salida_multiple_service)
    ],
) -> MovimientoPendienteResponse:
    pendiente = await service.ejecutar(
        RegistrarSalidaMultipleInput(
            productos=[
                ItemSalidaMultipleInput(
                    producto_codigo=item.producto_codigo,
                    cantidad=item.cantidad,
                    ubicacion=item.ubicacion,
                )
                for item in payload.productos
            ],
            motivo=payload.motivo,
            cliente_destino=payload.cliente_destino,
            notas=payload.notas,
        ),
        _audit_persona(usuario_actual),
    )
    return _movimiento_pendiente_response(pendiente)


@router.get(
    "",
    response_model=MovimientosPendientesPaginadosResponse,
    summary="Lista propuestas pendientes — super_admin ve todas, el resto solo las propias",
)
async def listar_movimientos_pendientes(
    entrada: Annotated[
        ListarMovimientosPendientesInput, Depends(get_listar_movimientos_pendientes_input)
    ],
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ListarMovimientosPendientesService, Depends(get_listar_movimientos_pendientes_service)
    ],
) -> MovimientosPendientesPaginadosResponse:
    resultado = await service.ejecutar(
        entrada,
        usuario_actual_id=usuario_actual.id,
        es_super_admin=_es_super_admin(usuario_actual),
    )
    return MovimientosPendientesPaginadosResponse(
        resultado=[_movimiento_pendiente_response(p) for p in resultado.resultado],
        pagina_actual=resultado.pagina_actual,
        elementos_por_pagina=resultado.elementos_por_pagina,
        total_elementos=resultado.total_elementos,
        total_paginas=resultado.total_paginas,
    )


@router.delete(
    "/eliminar-multiples",
    response_model=EliminarMovimientosPendientesMultiplesResponse,
    summary="Elimina varias propuestas pendientes de una vez (requiere super_admin)",
)
async def eliminar_movimientos_pendientes_multiples(
    payload: EliminarMovimientosPendientesMultiplesRequest,
    _usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        EliminarMovimientosPendientesMultiplesService,
        Depends(get_eliminar_movimientos_pendientes_multiples_service),
    ],
) -> EliminarMovimientosPendientesMultiplesResponse:
    resultado = await service.ejecutar(payload.movimientos_pendientes_ids)
    return EliminarMovimientosPendientesMultiplesResponse(**resultado)


@router.delete(
    "/{movimiento_pendiente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una propuesta pendiente (el dueño, o super_admin)",
    responses={
        403: {"description": "La propuesta no pertenece a este usuario"},
        404: {"description": "No existe una propuesta con ese id"},
        409: {"description": "La propuesta ya fue confirmada"},
    },
)
async def eliminar_movimiento_pendiente(
    movimiento_pendiente_id: str,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        EliminarMovimientoPendienteService, Depends(get_eliminar_movimiento_pendiente_service)
    ],
) -> None:
    await service.ejecutar(
        movimiento_pendiente_id,
        usuario_actual_id=usuario_actual.id,
        es_super_admin=_es_super_admin(usuario_actual),
    )


@router.post(
    "/{movimiento_pendiente_id}/confirmar",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirma una propuesta pendiente, aplicando el movimiento real (exclusivo super_admin)",
    responses={
        404: {"description": "No existe una propuesta con ese id"},
        409: {"description": "La propuesta ya fue confirmada"},
    },
)
async def confirmar_movimiento_pendiente(
    movimiento_pendiente_id: str,
    usuario_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        ConfirmarMovimientoPendienteService, Depends(get_confirmar_movimiento_pendiente_service)
    ],
) -> MovimientoResponse:
    movimiento = await service.ejecutar(movimiento_pendiente_id, _audit_persona(usuario_actual))
    return _movimiento_response(movimiento)
