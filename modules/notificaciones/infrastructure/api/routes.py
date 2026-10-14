from typing import Annotated

from fastapi import APIRouter, Depends, Query

from modules.notificaciones.application.ports.configuracion_correo import ConfiguracionCorreoPort
from modules.notificaciones.application.services.listar_notificaciones import (
    ListarNotificacionesService,
)
from modules.notificaciones.application.services.procesar_recordatorios import (
    ProcesarRecordatoriosService,
)
from modules.notificaciones.application.services.reenviar_notificacion import (
    ReenviarNotificacionService,
)
from modules.notificaciones.domain.entities import EstadoNotificacion
from modules.notificaciones.infrastructure.api.dependencies import (
    get_configuracion_correo,
    get_listar_notificaciones_service,
    get_procesar_recordatorios_service,
    get_reenviar_notificacion_service,
)
from modules.notificaciones.infrastructure.api.schemas import (
    EstadoCorreoResponse,
    NotificacionResponse,
    ResultadoRecordatoriosResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.planificador import requiere_admin_o_planificador
from shared.infrastructure.api.dependencies.user_authentication import requiere_permiso

router = APIRouter(prefix="/api/notificaciones", tags=["notificaciones"])

_requiere_notificaciones_gestionar = requiere_permiso("notificaciones-gestionar")
_requiere_notificaciones_ver = requiere_permiso("notificaciones-ver")


def _a_response(notificacion) -> NotificacionResponse:
    return NotificacionResponse(
        id=notificacion.id,
        destinatarios=notificacion.destinatarios,
        correos=notificacion.correos,
        asunto=notificacion.asunto,
        cuerpo=notificacion.cuerpo,
        estado=notificacion.estado,
        detalle=notificacion.detalle,
        intentos=notificacion.intentos,
        creada_en=notificacion.creada_en,
        actualizada_en=notificacion.actualizada_en,
    )


@router.get("", summary="Historial de los correos enviados por el sistema (solo administrador general)")
async def listar_notificaciones(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_notificaciones_ver)],
    service: Annotated[ListarNotificacionesService, Depends(get_listar_notificaciones_service)],
    estado: EstadoNotificacion | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    listado = await service.ejecutar(estado, skip, limit)
    return {
        "status": "success",
        "data": [_a_response(n).model_dump() for n in listado.items],
        "meta": {"total": listado.total, "skip": listado.skip, "limit": listado.limit},
    }


@router.get("/estado-correo", summary="Si el envio de correo esta configurado (solo administrador general)")
async def estado_correo(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_notificaciones_ver)],
    configuracion: Annotated[ConfiguracionCorreoPort, Depends(get_configuracion_correo)],
):
    respuesta = EstadoCorreoResponse(
        configurado=configuracion.esta_configurado(), remitente=configuracion.remitente()
    )
    return {"status": "success", "data": respuesta.model_dump()}


@router.post(
    "/procesar-recordatorios",
    summary="Envia los recordatorios pendientes: proximos mantenimientos y devoluciones",
    responses={403: {"description": "Ni el administrador general ni el planificador autorizado"}},
)
async def procesar_recordatorios(
    _: Annotated[None, Depends(requiere_admin_o_planificador)],
    service: Annotated[ProcesarRecordatoriosService, Depends(get_procesar_recordatorios_service)],
):
    resultado = await service.ejecutar()
    respuesta = ResultadoRecordatoriosResponse(
        mantenimientos_avisados=resultado.mantenimientos_avisados,
        devoluciones_recordadas=resultado.devoluciones_recordadas,
        errores=resultado.errores,
    )
    return {"status": "success", "data": respuesta.model_dump()}


@router.post(
    "/{id_notificacion}/reenviar",
    summary="Reintenta una notificacion que fallo o se omitio (solo administrador general)",
    responses={
        404: {"description": "La notificacion no existe"},
        422: {"description": "La notificacion ya se envio"},
    },
)
async def reenviar_notificacion(
    id_notificacion: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_notificaciones_gestionar)],
    service: Annotated[ReenviarNotificacionService, Depends(get_reenviar_notificacion_service)],
):
    notificacion = await service.ejecutar(id_notificacion)
    return {"status": "success", "data": _a_response(notificacion).model_dump()}
