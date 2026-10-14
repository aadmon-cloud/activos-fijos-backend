from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from modules.movimientos.application.dto.acciones_movimiento_dto import (
    ConfirmarDevolucionDTO,
    ConfirmarSalidaDTO,
    SolicitarDevolucionDTO,
)
from modules.movimientos.application.dto.actor_movimiento_dto import ActorMovimientoDTO
from modules.movimientos.application.dto.aprobar_movimiento_dto import AprobarMovimientoDTO
from modules.movimientos.application.dto.chequeo_movimiento_dto import (
    AceptarActaDTO,
    ChequearItemDTO,
    ObtenerActaDTO,
)
from modules.movimientos.application.dto.listar_movimientos_dto import ListarMovimientosDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO
from modules.movimientos.application.dto.obtener_movimiento_dto import ObtenerMovimientoDTO
from modules.movimientos.application.dto.rechazar_movimiento_dto import RechazarMovimientoDTO
from modules.movimientos.application.dto.solicitar_movimiento_dto import SolicitarMovimientoDTO
from modules.movimientos.application.services.aceptar_acta_movimiento import (
    AceptarActaMovimientoService,
)
from modules.movimientos.application.services.aprobar_movimiento import AprobarMovimientoService
from modules.movimientos.application.services.chequear_item_movimiento import (
    ChequearItemMovimientoService,
)
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
from modules.movimientos.application.services.obtener_acta_movimiento import (
    ObtenerActaMovimientoService,
)
from modules.movimientos.application.services.obtener_comprobante_movimiento import (
    ObtenerComprobanteMovimientoService,
)
from modules.movimientos.application.services.obtener_movimiento import ObtenerMovimientoService
from modules.movimientos.application.services.rechazar_movimiento import RechazarMovimientoService
from modules.movimientos.application.services.solicitar_devolucion_movimiento import (
    SolicitarDevolucionMovimientoService,
)
from modules.movimientos.application.services.solicitar_movimiento import (
    SolicitarMovimientoService,
)
from modules.movimientos.domain.entities import EstadoMovimiento, TipoMovimiento
from modules.movimientos.infrastructure.api.dependencies import (
    get_aceptar_acta_movimiento_service,
    get_aprobar_movimiento_service,
    get_chequear_item_movimiento_service,
    get_confirmar_devolucion_movimiento_service,
    get_confirmar_salida_movimiento_service,
    get_ejecutar_baja_movimiento_service,
    get_listar_movimientos_service,
    get_obtener_acta_movimiento_service,
    get_obtener_comprobante_movimiento_service,
    get_obtener_movimiento_service,
    get_rechazar_movimiento_service,
    get_solicitar_devolucion_movimiento_service,
    get_solicitar_movimiento_service,
)
from modules.movimientos.infrastructure.api.schemas import (
    AccionSobreActivosRequest,
    ChequeoItemRequest,
    ConfirmarSalidaRequest,
    MovimientoResponse,
    RechazarMovimientoRequest,
    SolicitarMovimientoRequest,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_permiso,
    tiene_permiso,
)

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])

_requiere_movimientos_gestionar = requiere_permiso("movimientos-gestionar")
_requiere_movimientos_solicitar = requiere_permiso("movimientos-solicitar")
_requiere_movimientos_ver = requiere_permiso("movimientos-ver")


def _a_response(movimiento: MovimientoDTO) -> dict:
    return MovimientoResponse.model_validate(asdict(movimiento)).model_dump()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Solicita un movimiento (prestamo, salida para evento o baja) sobre uno o varios activos",
    responses={
        403: {"description": "Baja solo para administradores, prestar activos ajenos o elegir otro destinatario"},
        404: {"description": "Un activo o el usuario destino no existen"},
        409: {"description": "Un activo ya tiene un movimiento en curso"},
        422: {"description": "Un activo no esta disponible"},
    },
)
async def solicitar_movimiento(
    body: SolicitarMovimientoRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_solicitar)],
    service: Annotated[SolicitarMovimientoService, Depends(get_solicitar_movimiento_service)],
):
    movimiento = await service.ejecutar(
        SolicitarMovimientoDTO(
            tipo=body.tipo,
            activo_ids=body.activo_ids,
            descripcion=body.descripcion,
            sentido=body.sentido,
            usuario_destino_id=body.usuario_destino_id,
            evento_nombre=body.evento_nombre,
            fecha_salida_estimada=body.fecha_salida_estimada,
            fecha_retorno_estimada=body.fecha_retorno_estimada,
            solicitante_id=identidad.id_usuario,
            solicitante_nombre=identidad.nombre,
            solicitante_rol=identidad.rol,
            puede_solicitar_baja=await tiene_permiso(identidad.rol, "movimientos-baja"),
            puede_elegir_destinatario=await tiene_permiso(identidad.rol, "movimientos-destinatario"),
        )
    )
    return {
        "status": "success",
        "message": "Movimiento solicitado exitosamente.",
        "data": _a_response(movimiento),
    }


@router.get("", summary="Lista los movimientos existentes")
async def listar_movimientos(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[ListarMovimientosService, Depends(get_listar_movimientos_service)],
    tipo: TipoMovimiento | None = Query(default=None),
    estado: EstadoMovimiento | None = Query(default=None),
    activo_id: str | None = Query(default=None),
    usuario_destino_id: str | None = Query(default=None),
    creado_por_id: str | None = Query(default=None),
    para_mi: bool = Query(
        default=False,
        description="Solo lo que le concierne como responsable o destinatario (al administrador, ademas, lo que espera su accion).",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    listado = await service.ejecutar(
        ListarMovimientosDTO(
            actor_id=identidad.id_usuario,
            actor_rol=identidad.rol,
            tipo=tipo,
            estado=estado,
            activo_id=activo_id,
            usuario_destino_id=usuario_destino_id,
            creado_por_id=creado_por_id,
            para_mi=para_mi,
            skip=skip,
            limit=limit,
        )
    )
    return {
        "status": "success",
        "data": [_a_response(m) for m in listado.items],
        "meta": {"total": listado.total, "skip": listado.skip, "limit": listado.limit},
    }


@router.get(
    "/{id_movimiento}",
    summary="Obtiene un movimiento por id",
    responses={404: {"description": "El movimiento no existe"}},
)
async def obtener_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[ObtenerMovimientoService, Depends(get_obtener_movimiento_service)],
):
    movimiento = await service.ejecutar(
        ObtenerMovimientoDTO(
            id_movimiento=id_movimiento, actor_id=identidad.id_usuario, actor_rol=identidad.rol
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/aprobar",
    summary="El responsable aprueba sus activos (o administracion aprueba una baja)",
    responses={
        403: {"description": "El usuario no puede decidir sobre ninguno de los activos"},
        404: {"description": "El movimiento no existe"},
        422: {"description": "El movimiento no espera ninguna aprobacion"},
    },
)
async def aprobar_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[AprobarMovimientoService, Depends(get_aprobar_movimiento_service)],
    body: AccionSobreActivosRequest | None = None,
):
    movimiento = await service.ejecutar(
        AprobarMovimientoDTO(
            id_movimiento=id_movimiento,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
            activo_ids=body.activo_ids if body else None,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/rechazar",
    summary="Rechaza, con motivo, los activos que el usuario puede decidir en el paso actual",
    responses={
        400: {"description": "Falta el motivo del rechazo"},
        403: {"description": "El usuario no puede decidir sobre ninguno de los activos"},
        404: {"description": "El movimiento no existe"},
        422: {"description": "El movimiento no espera ninguna decision"},
    },
)
async def rechazar_movimiento(
    id_movimiento: str,
    body: RechazarMovimientoRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[RechazarMovimientoService, Depends(get_rechazar_movimiento_service)],
):
    movimiento = await service.ejecutar(
        RechazarMovimientoDTO(
            id_movimiento=id_movimiento,
            motivo_rechazo=body.motivo_rechazo,
            activo_ids=body.activo_ids,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.put(
    "/{id_movimiento}/items/{activo_id}/chequeo",
    summary="Administracion marca un activo en el chequeo de salida o de ingreso (se guarda al instante)",
    responses={
        403: {"description": "El activo no esta en una fase que se pueda chequear, o falta el permiso"},
        404: {"description": "El movimiento no existe"},
        422: {"description": "Falta describir la novedad, o el activo no hace parte del movimiento"},
    },
)
async def chequear_item_movimiento(
    id_movimiento: str,
    activo_id: str,
    body: ChequeoItemRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_gestionar)],
    service: Annotated[ChequearItemMovimientoService, Depends(get_chequear_item_movimiento_service)],
):
    movimiento = await service.ejecutar(
        ChequearItemDTO(
            id_movimiento=id_movimiento,
            activo_id=activo_id,
            resultado=body.resultado,
            observacion=body.observacion,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/confirmar-salida",
    summary="Cierra el chequeo de salida: sale lo encontrado, se genera el acta de salida (prestamo o evento)",
    responses={
        404: {"description": "El movimiento no existe"},
        422: {"description": "No hay activos chequeados como encontrados, o el cambio sobre un activo fallo"},
    },
)
async def confirmar_salida_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_gestionar)],
    service: Annotated[
        ConfirmarSalidaMovimientoService, Depends(get_confirmar_salida_movimiento_service)
    ],
    body: ConfirmarSalidaRequest | None = None,
):
    movimiento = await service.ejecutar(
        ConfirmarSalidaDTO(
            id_movimiento=id_movimiento,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_correo=identidad.email,
            motivo_no_incluidos=body.motivo_no_incluidos if body else None,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/solicitar-devolucion",
    summary="Quien tiene los activos pide devolverlos (todos o algunos)",
    responses={
        403: {"description": "El usuario no tiene ninguno de los activos"},
        404: {"description": "El movimiento no existe"},
        422: {"description": "El movimiento no tiene activos fuera"},
    },
)
async def solicitar_devolucion_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[
        SolicitarDevolucionMovimientoService, Depends(get_solicitar_devolucion_movimiento_service)
    ],
    body: AccionSobreActivosRequest | None = None,
):
    movimiento = await service.ejecutar(
        SolicitarDevolucionDTO(
            id_movimiento=id_movimiento,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
            activo_ids=body.activo_ids if body else None,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/confirmar-devolucion",
    summary="Cierra el chequeo de ingreso: se reciben los activos encontrados y se genera el acta de ingreso",
    responses={
        404: {"description": "El movimiento no existe"},
        422: {"description": "No hay activos fuera, ninguno chequeado como encontrado, o el cambio sobre un activo fallo"},
    },
)
async def confirmar_devolucion_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_gestionar)],
    service: Annotated[
        ConfirmarDevolucionMovimientoService, Depends(get_confirmar_devolucion_movimiento_service)
    ],
):
    movimiento = await service.ejecutar(
        ConfirmarDevolucionDTO(
            id_movimiento=id_movimiento,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_correo=identidad.email,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.post(
    "/{id_movimiento}/actas/{acta_id}/aceptar",
    summary="Quien retira o devuelve los activos acepta el acta (queda su sello con nombre y correo)",
    responses={
        403: {"description": "Solo el responsable que retira o devuelve puede aceptar el acta"},
        404: {"description": "El movimiento o el acta no existen"},
        409: {"description": "El acta ya fue aceptada"},
    },
)
async def aceptar_acta_movimiento(
    id_movimiento: str,
    acta_id: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[AceptarActaMovimientoService, Depends(get_aceptar_acta_movimiento_service)],
):
    movimiento = await service.ejecutar(
        AceptarActaDTO(
            id_movimiento=id_movimiento,
            acta_id=acta_id,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_correo=identidad.email,
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.get(
    "/{id_movimiento}/actas/{acta_id}/pdf",
    summary="Descarga el PDF de un acta de salida o de ingreso",
    responses={404: {"description": "El movimiento o el acta no existen"}},
)
async def obtener_acta_movimiento(
    id_movimiento: str,
    acta_id: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[ObtenerActaMovimientoService, Depends(get_obtener_acta_movimiento_service)],
):
    archivo = await service.ejecutar(
        ObtenerActaDTO(
            id_movimiento=id_movimiento, acta_id=acta_id, actor_id=identidad.id_usuario, actor_rol=identidad.rol
        )
    )
    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
        },
    )


@router.post(
    "/{id_movimiento}/ejecutar-baja",
    summary="Ejecuta la baja del activo, dejandolo dado_de_baja de forma definitiva",
    responses={
        404: {"description": "El movimiento no existe"},
        422: {"description": "El movimiento no esta aprobado, o el cambio sobre el activo fallo"},
    },
)
async def ejecutar_baja_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_gestionar)],
    service: Annotated[EjecutarBajaMovimientoService, Depends(get_ejecutar_baja_movimiento_service)],
):
    movimiento = await service.ejecutar(
        ActorMovimientoDTO(
            id_movimiento=id_movimiento, actor_id=identidad.id_usuario, actor_nombre=identidad.nombre
        )
    )
    return {"status": "success", "data": _a_response(movimiento)}


@router.get(
    "/{id_movimiento}/comprobante",
    summary="Descarga el comprobante PDF de una salida para evento",
    responses={404: {"description": "El movimiento no existe o aun no tiene comprobante generado"}},
)
async def obtener_comprobante_movimiento(
    id_movimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_movimientos_ver)],
    service: Annotated[
        ObtenerComprobanteMovimientoService, Depends(get_obtener_comprobante_movimiento_service)
    ],
):
    archivo = await service.ejecutar(
        ObtenerMovimientoDTO(
            id_movimiento=id_movimiento, actor_id=identidad.id_usuario, actor_rol=identidad.rol
        )
    )
    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
        },
    )
