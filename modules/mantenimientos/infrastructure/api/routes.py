from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from modules.mantenimientos.application.dto.cambiar_estado_mantenimiento_dto import (
    CambiarEstadoMantenimientoDTO,
)
from modules.mantenimientos.application.dto.crear_mantenimiento_dto import (
    CrearMantenimientoDTO,
)
from modules.mantenimientos.application.dto.crear_mantenimientos_masivo_dto import (
    CrearMantenimientosMasivoDTO,
)
from modules.mantenimientos.application.dto.eliminar_archivo_mantenimiento_dto import (
    EliminarArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.dto.listar_mantenimientos_dto import (
    ListarMantenimientosDTO,
)
from modules.mantenimientos.application.dto.mantenimiento_con_nombres_dto import (
    MantenimientoConNombresDTO,
)
from modules.mantenimientos.application.dto.mantenimiento_dto import MantenimientoDTO
from modules.mantenimientos.application.dto.subir_archivo_mantenimiento_dto import (
    SubirArchivoMantenimientoDTO,
)
from modules.mantenimientos.application.services.cambiar_estado_mantenimiento import (
    CambiarEstadoMantenimientoService,
)
from modules.mantenimientos.application.services.crear_mantenimiento import (
    CrearMantenimientoService,
)
from modules.mantenimientos.application.services.eliminar_archivo_mantenimiento import (
    EliminarArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.listar_mantenimientos import (
    ListarMantenimientosService,
)
from modules.mantenimientos.application.services.obtener_archivo_mantenimiento import (
    ObtenerArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.obtener_mantenimiento import (
    ObtenerMantenimientoService,
)
from modules.mantenimientos.application.services.registrar_mantenimientos_masivo import (
    RegistrarMantenimientosMasivoService,
)
from modules.mantenimientos.application.services.subir_archivo_mantenimiento import (
    TAMANO_MAXIMO_ARCHIVO_BYTES,
    SubirArchivoMantenimientoService,
)
from modules.mantenimientos.application.services.verificar_alertas_mantenimiento import (
    VerificarAlertasMantenimientoService,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, TipoMantenimiento
from modules.mantenimientos.domain.errors import ArchivoDemasiadoGrandeError
from modules.mantenimientos.infrastructure.api.dependencies import (
    get_cambiar_estado_mantenimiento_service,
    get_crear_mantenimiento_service,
    get_eliminar_archivo_mantenimiento_service,
    get_listar_mantenimientos_service,
    get_obtener_archivo_mantenimiento_service,
    get_obtener_mantenimiento_service,
    get_registrar_mantenimientos_masivo_service,
    get_subir_archivo_mantenimiento_service,
    get_verificar_alertas_mantenimiento_service,
)
from modules.mantenimientos.infrastructure.api.schemas import (
    ArchivoMantenimientoResponse,
    CambiarEstadoMantenimientoRequest,
    CrearMantenimientoRequest,
    CrearMantenimientosMasivoRequest,
    MantenimientoConNombresResponse,
    MantenimientoResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import requiere_rol

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"
_ROL_MANTENIMIENTO = "mantenimiento"

router = APIRouter(prefix="/api/mantenimientos", tags=["mantenimientos"])

_requiere_mantenimiento = requiere_rol(_ROL_MANTENIMIENTO, _ROL_ADMINISTRADOR_GENERAL)
_requiere_administrador_general = requiere_rol(_ROL_ADMINISTRADOR_GENERAL)


def _a_response(mantenimiento: MantenimientoDTO) -> MantenimientoResponse:
    return MantenimientoResponse(
        id=mantenimiento.id,
        activo_id=mantenimiento.activo_id,
        solicitud_id=mantenimiento.solicitud_id,
        tipo=mantenimiento.tipo,
        tecnico_responsable_id=mantenimiento.tecnico_responsable_id,
        fecha=mantenimiento.fecha,
        observaciones=mantenimiento.observaciones,
        costo=mantenimiento.costo,
        documentos=[
            ArchivoMantenimientoResponse(archivo_id=a.archivo_id, nombre=a.nombre)
            for a in mantenimiento.documentos
        ],
        evidencias=[
            ArchivoMantenimientoResponse(archivo_id=a.archivo_id, nombre=a.nombre)
            for a in mantenimiento.evidencias
        ],
        estado=mantenimiento.estado,
        frecuencia_dias=mantenimiento.frecuencia_dias,
        proxima_fecha_sugerida=mantenimiento.proxima_fecha_sugerida,
        alerta_enviada=mantenimiento.alerta_enviada,
        creado_por_id=mantenimiento.creado_por_id,
        creado_por_nombre=mantenimiento.creado_por_nombre,
        fecha_creacion=mantenimiento.fecha_creacion,
    )


def _a_response_con_nombres(
    mantenimiento: MantenimientoConNombresDTO,
) -> MantenimientoConNombresResponse:
    base = _a_response(mantenimiento).model_dump()
    return MantenimientoConNombresResponse(
        **base,
        activo_nombre=mantenimiento.activo_nombre,
        activo_numero_inventario=mantenimiento.activo_numero_inventario,
        tecnico_nombre=mantenimiento.tecnico_nombre,
        estados_permitidos=mantenimiento.estados_permitidos,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuevo mantenimiento",
    responses={
        404: {"description": "El activo no existe"},
        422: {"description": "El tecnico no tiene el rol de mantenimiento"},
    },
)
async def crear_mantenimiento(
    body: CrearMantenimientoRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[CrearMantenimientoService, Depends(get_crear_mantenimiento_service)],
):
    mantenimiento = await service.ejecutar(
        CrearMantenimientoDTO(
            activo_id=body.activo_id,
            tipo=body.tipo,
            tecnico_responsable_id=body.tecnico_responsable_id,
            fecha=body.fecha,
            solicitud_id=body.solicitud_id,
            observaciones=body.observaciones,
            costo=body.costo,
            frecuencia_dias=body.frecuencia_dias,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Mantenimiento creado exitosamente.",
        "data": {"id": mantenimiento.id},
    }


@router.post(
    "/masivo",
    summary="Registra un mismo mantenimiento ya realizado sobre varios activos, por su codigo",
    responses={
        400: {"description": "Lista de codigos vacia o demasiado larga"},
        422: {"description": "El tecnico no tiene el rol de mantenimiento"},
    },
)
async def registrar_mantenimientos_masivo(
    body: CrearMantenimientosMasivoRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        RegistrarMantenimientosMasivoService, Depends(get_registrar_mantenimientos_masivo_service)
    ],
):
    resultado = await service.ejecutar(
        CrearMantenimientosMasivoDTO(
            codigos=body.codigos,
            tipo=body.tipo,
            tecnico_responsable_id=body.tecnico_responsable_id,
            fecha=body.fecha,
            observaciones=body.observaciones,
            costo=body.costo,
            frecuencia_dias=body.frecuencia_dias,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "data": {
            "registrados": [
                {
                    "codigo": r.codigo,
                    "activo_id": r.activo_id,
                    "mantenimiento_id": r.mantenimiento_id,
                }
                for r in resultado.registrados
            ],
            "no_encontrados": resultado.no_encontrados,
        },
    }


@router.get(
    "",
    summary="Lista los mantenimientos existentes",
)
async def listar_mantenimientos(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[ListarMantenimientosService, Depends(get_listar_mantenimientos_service)],
    activo_id: str | None = Query(default=None),
    tecnico_responsable_id: str | None = Query(default=None),
    estado: EstadoMantenimiento | None = Query(default=None),
    tipo: TipoMantenimiento | None = Query(default=None),
    solicitud_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    listado = await service.ejecutar(
        ListarMantenimientosDTO(
            activo_id=activo_id,
            tecnico_responsable_id=tecnico_responsable_id,
            estado=estado,
            tipo=tipo,
            solicitud_id=solicitud_id,
            skip=skip,
            limit=limit,
        )
    )
    return {
        "status": "success",
        "data": [_a_response_con_nombres(m).model_dump() for m in listado.items],
        "meta": {"total": listado.total, "skip": listado.skip, "limit": listado.limit},
    }


@router.get(
    "/{id_mantenimiento}",
    summary="Obtiene un mantenimiento por id",
    responses={404: {"description": "El mantenimiento no existe"}},
)
async def obtener_mantenimiento(
    id_mantenimiento: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[ObtenerMantenimientoService, Depends(get_obtener_mantenimiento_service)],
):
    mantenimiento = await service.ejecutar(id_mantenimiento)
    return {"status": "success", "data": _a_response_con_nombres(mantenimiento).model_dump()}


@router.put(
    "/{id_mantenimiento}/estado",
    summary="Cambia el estado de un mantenimiento",
    responses={
        404: {"description": "El mantenimiento no existe"},
        422: {"description": "La transicion de estado no es valida"},
    },
)
async def cambiar_estado_mantenimiento(
    id_mantenimiento: str,
    body: CambiarEstadoMantenimientoRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        CambiarEstadoMantenimientoService, Depends(get_cambiar_estado_mantenimiento_service)
    ],
):
    mantenimiento = await service.ejecutar(
        CambiarEstadoMantenimientoDTO(
            id_mantenimiento=id_mantenimiento,
            estado_nuevo=body.estado_nuevo,
            actor_id=identidad.id_usuario,
            actor_nombre=identidad.nombre,
            actor_rol=identidad.rol,
            actor_area_id=identidad.area_id,
        )
    )
    return {"status": "success", "data": _a_response(mantenimiento).model_dump()}


async def _subir_archivo(
    id_mantenimiento: str,
    nombre: str,
    categoria: str,
    request: Request,
    identidad: IdentidadUsuarioAutenticada,
    service: SubirArchivoMantenimientoService,
):
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > TAMANO_MAXIMO_ARCHIVO_BYTES:
        raise ArchivoDemasiadoGrandeError()

    mantenimiento = await service.ejecutar(
        SubirArchivoMantenimientoDTO(
            id_mantenimiento=id_mantenimiento,
            nombre=nombre,
            contenido=await request.body(),
            categoria=categoria,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": _a_response(mantenimiento).model_dump()}


@router.post(
    "/{id_mantenimiento}/documentos",
    status_code=status.HTTP_201_CREATED,
    summary="Sube un documento de soporte del mantenimiento",
    responses={
        400: {"description": "No es un archivo JPEG, PNG, WebP o PDF, o supera el tamano maximo"},
        404: {"description": "El mantenimiento no existe"},
    },
)
async def subir_documento_mantenimiento(
    id_mantenimiento: str,
    request: Request,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        SubirArchivoMantenimientoService, Depends(get_subir_archivo_mantenimiento_service)
    ],
    nombre: str = Query(...),
):
    return await _subir_archivo(id_mantenimiento, nombre, "documento", request, identidad, service)


@router.post(
    "/{id_mantenimiento}/evidencias",
    status_code=status.HTTP_201_CREATED,
    summary="Sube una evidencia fotografica del mantenimiento",
    responses={
        400: {"description": "No es un archivo JPEG, PNG, WebP o PDF, o supera el tamano maximo"},
        404: {"description": "El mantenimiento no existe"},
    },
)
async def subir_evidencia_mantenimiento(
    id_mantenimiento: str,
    request: Request,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        SubirArchivoMantenimientoService, Depends(get_subir_archivo_mantenimiento_service)
    ],
    nombre: str = Query(...),
):
    return await _subir_archivo(id_mantenimiento, nombre, "evidencia", request, identidad, service)


@router.get(
    "/{id_mantenimiento}/archivos/{archivo_id}",
    summary="Descarga un documento o evidencia del mantenimiento",
    responses={404: {"description": "El archivo no existe en este mantenimiento"}},
)
async def obtener_archivo_mantenimiento(
    id_mantenimiento: str,
    archivo_id: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        ObtenerArchivoMantenimientoService, Depends(get_obtener_archivo_mantenimiento_service)
    ],
):
    archivo = await service.ejecutar(id_mantenimiento, archivo_id)
    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={"Cache-Control": "private, max-age=300", "Content-Disposition": "inline"},
    )


@router.delete(
    "/{id_mantenimiento}/archivos/{archivo_id}",
    summary="Elimina un documento o evidencia del mantenimiento",
    responses={404: {"description": "El archivo no existe en este mantenimiento"}},
)
async def eliminar_archivo_mantenimiento(
    id_mantenimiento: str,
    archivo_id: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(_requiere_mantenimiento)],
    service: Annotated[
        EliminarArchivoMantenimientoService, Depends(get_eliminar_archivo_mantenimiento_service)
    ],
):
    mantenimiento = await service.ejecutar(
        EliminarArchivoMantenimientoDTO(
            id_mantenimiento=id_mantenimiento,
            archivo_id=archivo_id,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": _a_response(mantenimiento).model_dump()}


@router.post(
    "/verificar-alertas",
    summary="Revisa los mantenimientos con proxima fecha sugerida y envia las notificaciones pendientes",
)
async def verificar_alertas_mantenimiento(
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[
        VerificarAlertasMantenimientoService, Depends(get_verificar_alertas_mantenimiento_service)
    ],
):
    cantidad = await service.ejecutar()
    return {"status": "success", "data": {"notificaciones_enviadas": cantidad}}
