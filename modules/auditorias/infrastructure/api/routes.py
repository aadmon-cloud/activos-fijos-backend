from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from modules.auditorias.application.dto.cerrar_auditoria_dto import CerrarAuditoriaDTO
from modules.auditorias.application.dto.iniciar_auditoria_dto import IniciarAuditoriaDTO
from modules.auditorias.application.dto.listar_auditorias_dto import ListarAuditoriasDTO
from modules.auditorias.application.dto.verificar_item_auditoria_dto import (
    VerificarItemAuditoriaDTO,
)
from modules.auditorias.application.services.cerrar_auditoria import CerrarAuditoriaService
from modules.auditorias.application.services.iniciar_auditoria import IniciarAuditoriaService
from modules.auditorias.application.services.listar_auditorias import ListarAuditoriasService
from modules.auditorias.application.services.obtener_auditoria import ObtenerAuditoriaService
from modules.auditorias.application.services.obtener_pdf_auditoria import (
    ObtenerPdfAuditoriaService,
)
from modules.auditorias.application.services.reenviar_notificacion_auditoria import (
    ReenviarNotificacionAuditoriaService,
)
from modules.auditorias.application.services.verificar_item_auditoria import (
    VerificarItemAuditoriaService,
)
from modules.auditorias.domain.entities import EstadoAuditoria
from modules.auditorias.infrastructure.api.dependencies import (
    get_cerrar_auditoria_service,
    get_iniciar_auditoria_service,
    get_listar_auditorias_service,
    get_obtener_auditoria_service,
    get_obtener_pdf_auditoria_service,
    get_reenviar_notificacion_auditoria_service,
    get_verificar_item_auditoria_service,
)
from modules.auditorias.infrastructure.api.schemas import (
    AuditoriaConNombresResponse,
    AuditoriaResponse,
    IniciarAuditoriaRequest,
    ItemAuditoriaResponse,
    VerificarItemAuditoriaRequest,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import requiere_permiso

router = APIRouter(prefix="/api/auditorias", tags=["auditorias"])

_requiere_auditorias_gestionar = requiere_permiso("auditorias-gestionar")
_requiere_auditorias_ver = requiere_permiso("auditorias-ver")


def _a_response(auditoria) -> AuditoriaResponse:
    return AuditoriaResponse(
        id=auditoria.id,
        usuario_auditado_id=auditoria.usuario_auditado_id,
        estado=auditoria.estado,
        items=[
            ItemAuditoriaResponse(
                activo_id=item.activo_id,
                nombre=item.nombre,
                numero_inventario=item.numero_inventario,
                tipo=item.tipo,
                descripcion=item.descripcion,
                serie=item.serie,
                estado_ciclo_vida_al_inicio=item.estado_ciclo_vida_al_inicio,
                resultado=item.resultado,
                observacion=item.observacion,
                verificado_en=item.verificado_en,
            )
            for item in auditoria.items
        ],
        fecha_inicio=auditoria.fecha_inicio,
        fecha_cierre=auditoria.fecha_cierre,
        pdf_archivo_id=auditoria.pdf_archivo_id,
        detalle_error_notificacion=auditoria.detalle_error_notificacion,
        auditor_id=auditoria.auditor_id,
        auditor_nombre=auditoria.auditor_nombre,
        total=auditoria.total,
        encontrados=auditoria.encontrados,
        encontrados_con_novedad=auditoria.encontrados_con_novedad,
        no_encontrados=auditoria.no_encontrados,
        pendientes=auditoria.pendientes,
    )


def _a_response_con_nombres(auditoria) -> AuditoriaConNombresResponse:
    base = _a_response(auditoria).model_dump()
    return AuditoriaConNombresResponse(
        **base,
        usuario_nombre=auditoria.usuario_nombre,
        usuario_identificacion=auditoria.usuario_identificacion,
        usuario_email=auditoria.usuario_email,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Inicia una auditoria de activos y elementos para un usuario",
    responses={404: {"description": "El usuario no existe"}},
)
async def iniciar_auditoria(
    body: IniciarAuditoriaRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_gestionar)],
    service: Annotated[IniciarAuditoriaService, Depends(get_iniciar_auditoria_service)],
):
    auditoria = await service.ejecutar(
        IniciarAuditoriaDTO(
            usuario_auditado_id=body.usuario_auditado_id,
            auditor_id=identidad.id_usuario,
            auditor_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Auditoria iniciada exitosamente.",
        "data": _a_response(auditoria).model_dump(),
    }


@router.get("", summary="Lista las auditorias existentes")
async def listar_auditorias(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_ver)],
    service: Annotated[ListarAuditoriasService, Depends(get_listar_auditorias_service)],
    usuario_auditado_id: str | None = Query(default=None),
    estado: EstadoAuditoria | None = Query(default=None),
    creado_por_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    listado = await service.ejecutar(
        ListarAuditoriasDTO(
            usuario_auditado_id=usuario_auditado_id,
            estado=estado,
            creado_por_id=creado_por_id,
            skip=skip,
            limit=limit,
        )
    )
    return {
        "status": "success",
        "data": [_a_response_con_nombres(a).model_dump() for a in listado.items],
        "meta": {"total": listado.total, "skip": listado.skip, "limit": listado.limit},
    }


@router.get(
    "/{id_auditoria}",
    summary="Obtiene una auditoria por id",
    responses={404: {"description": "La auditoria no existe"}},
)
async def obtener_auditoria(
    id_auditoria: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_ver)],
    service: Annotated[ObtenerAuditoriaService, Depends(get_obtener_auditoria_service)],
):
    auditoria = await service.ejecutar(id_auditoria)
    return {"status": "success", "data": _a_response_con_nombres(auditoria).model_dump()}


@router.put(
    "/{id_auditoria}/items/{activo_id}",
    summary="Registra el resultado de verificar un item de la auditoria",
    responses={
        400: {"description": "Falta la observacion obligatoria para 'encontrado_con_novedad'"},
        404: {"description": "La auditoria no existe, o el activo no forma parte de ella"},
        422: {"description": "La auditoria ya fue cerrada"},
    },
)
async def verificar_item_auditoria(
    id_auditoria: str,
    activo_id: str,
    body: VerificarItemAuditoriaRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_gestionar)],
    service: Annotated[
        VerificarItemAuditoriaService, Depends(get_verificar_item_auditoria_service)
    ],
):
    auditoria = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria=id_auditoria,
            activo_id=activo_id,
            resultado=body.resultado,
            observacion=body.observacion,
        )
    )
    return {"status": "success", "data": _a_response(auditoria).model_dump()}


@router.post(
    "/{id_auditoria}/cerrar",
    summary="Cierra la auditoria: marca pendientes como no encontrados, genera el PDF y envia la notificacion",
    responses={
        404: {"description": "La auditoria no existe"},
        422: {"description": "La auditoria ya fue cerrada"},
    },
)
async def cerrar_auditoria(
    id_auditoria: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_gestionar)],
    service: Annotated[CerrarAuditoriaService, Depends(get_cerrar_auditoria_service)],
):
    auditoria = await service.ejecutar(
        CerrarAuditoriaDTO(
            id_auditoria=id_auditoria, actor_id=identidad.id_usuario, actor_nombre=identidad.nombre
        )
    )
    return {"status": "success", "data": _a_response(auditoria).model_dump()}


@router.post(
    "/{id_auditoria}/reenviar-notificacion",
    summary="Reintenta el envio del correo de una auditoria ya cerrada",
    responses={
        404: {"description": "La auditoria no existe, o aun no tiene un PDF generado"},
        422: {"description": "La auditoria sigue en progreso"},
    },
)
async def reenviar_notificacion_auditoria(
    id_auditoria: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_gestionar)],
    service: Annotated[
        ReenviarNotificacionAuditoriaService,
        Depends(get_reenviar_notificacion_auditoria_service),
    ],
):
    auditoria = await service.ejecutar(id_auditoria)
    return {"status": "success", "data": _a_response(auditoria).model_dump()}


@router.get(
    "/{id_auditoria}/pdf",
    summary="Descarga el PDF generado de la auditoria",
    responses={404: {"description": "La auditoria no existe o aun no tiene un PDF generado"}},
)
async def obtener_pdf_auditoria(
    id_auditoria: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_auditorias_ver)],
    service: Annotated[ObtenerPdfAuditoriaService, Depends(get_obtener_pdf_auditoria_service)],
):
    archivo = await service.ejecutar(id_auditoria)
    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
        },
    )
