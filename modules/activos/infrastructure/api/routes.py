from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from modules.activos.application.dto.activo_con_nombres_dto import ActivoConNombresDTO
from modules.activos.application.dto.activo_dto import ActivoDTO
from modules.activos.application.dto.actualizar_activo_dto import ActualizarActivoDTO
from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.application.dto.complemento_dto import ComplementoDTO
from modules.activos.application.dto.crear_activo_dto import CrearActivoDTO
from modules.activos.application.dto.foto_dto import EliminarFotoActivoDTO, SubirFotoActivoDTO
from modules.activos.application.dto.listar_activos_dto import ListarActivosDTO
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import (
    CambiarEstadoActivoService,
)
from modules.activos.application.services.crear_activo import CrearActivoService
from modules.activos.application.services.eliminar_foto_activo import EliminarFotoActivoService
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.application.services.obtener_foto_activo import ObtenerFotoActivoService
from modules.activos.application.services.subir_foto_activo import SubirFotoActivoService
from modules.activos.application.services.obtener_activo import ObtenerActivoService
from modules.activos.application.services.obtener_historial_activo import (
    ObtenerHistorialActivoService,
)
from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.domain.errors import FotoDemasiadoGrandeError
from modules.activos.domain.fotos import TAMANO_MAXIMO_FOTO_BYTES
from modules.activos.infrastructure.api.dependencies import (
    get_actualizar_activo_service,
    get_cambiar_estado_activo_service,
    get_crear_activo_service,
    get_eliminar_foto_activo_service,
    get_listar_activos_service,
    get_obtener_activo_service,
    get_obtener_foto_activo_service,
    get_obtener_historial_activo_service,
    get_subir_foto_activo_service,
)
from modules.activos.infrastructure.api.schemas import (
    ActualizarActivoRequest,
    ActivoConNombresResponse,
    ActivoResponse,
    CambiarEstadoActivoRequest,
    ComplementoRequest,
    ComplementoResponse,
    CrearActivoRequest,
    EntradaHistorialResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"

router = APIRouter(prefix="/api/activos", tags=["activos"])

_requiere_administrador_general = requiere_rol(_ROL_ADMINISTRADOR_GENERAL)


def _a_complemento_dto(body: ComplementoRequest) -> ComplementoDTO:
    return ComplementoDTO(
        nombre=body.nombre, descripcion=body.descripcion, cantidad=body.cantidad, serie=body.serie
    )


def _a_response(activo: ActivoDTO) -> ActivoResponse:
    return ActivoResponse(
        id=activo.id,
        nombre=activo.nombre,
        numero_inventario=activo.numero_inventario,
        tipo=activo.tipo,
        marca=activo.marca,
        modelo=activo.modelo,
        serie=activo.serie,
        descripcion=activo.descripcion,
        categoria_id=activo.categoria_id,
        area_id=activo.area_id,
        responsable_id=activo.responsable_id,
        condicion_id=activo.condicion_id,
        estado_ciclo_vida=activo.estado_ciclo_vida,
        sede_id=activo.sede_id,
        lugar_id=activo.lugar_id,
        fecha_ingreso=activo.fecha_ingreso,
        complementos=[
            ComplementoResponse(
                nombre=c.nombre, descripcion=c.descripcion, cantidad=c.cantidad, serie=c.serie
            )
            for c in activo.complementos
        ],
        observaciones=activo.observaciones,
        foto_url=activo.foto_url,
        ficha_tecnica_url=activo.ficha_tecnica_url,
    )


def _a_response_con_nombres(activo: ActivoConNombresDTO) -> ActivoConNombresResponse:
    base = _a_response(activo).model_dump()

    return ActivoConNombresResponse(
        **base,
        categoria_nombre=activo.categoria_nombre,
        area_nombre=activo.area_nombre,
        responsable_nombre=activo.responsable_nombre,
        condicion_nombre=activo.condicion_nombre,
        condicion_color=activo.condicion_color,
        sede_nombre=activo.sede_nombre,
        lugar_nombre=activo.lugar_nombre,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuevo activo",
    responses={
        409: {"description": "Ya existe un activo con ese numero de inventario"},
        422: {"description": "Datos de entrada invalidos"},
    },
)
async def crear_activo(
    body: CrearActivoRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[CrearActivoService, Depends(get_crear_activo_service)],
):
    activo = await service.ejecutar(
        CrearActivoDTO(
            nombre=body.nombre,
            numero_inventario=body.numero_inventario,
            tipo=body.tipo,
            categoria_id=body.categoria_id,
            area_id=body.area_id,
            responsable_id=body.responsable_id,
            condicion_id=body.condicion_id,
            sede_id=body.sede_id,
            lugar_id=body.lugar_id,
            marca=body.marca,
            modelo=body.modelo,
            serie=body.serie,
            descripcion=body.descripcion,
            complementos=[_a_complemento_dto(c) for c in body.complementos],
            observaciones=body.observaciones,
            foto_url=body.foto_url,
            ficha_tecnica_url=body.ficha_tecnica_url,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Activo creado exitosamente.",
        "data": {"id": activo.id},
    }


@router.get(
    "",
    summary="Lista los activos existentes",
)
async def listar_activos(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarActivosService, Depends(get_listar_activos_service)],
    area_id: str | None = Query(default=None),
    categoria_id: str | None = Query(default=None),
    responsable_id: str | None = Query(default=None),
    condicion_id: str | None = Query(default=None),
    sede_id: str | None = Query(default=None),
    lugar_id: str | None = Query(default=None),
    estado_ciclo_vida: EstadoCicloVida | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    listado = await service.ejecutar(
        ListarActivosDTO(
            area_id=area_id,
            categoria_id=categoria_id,
            responsable_id=responsable_id,
            condicion_id=condicion_id,
            sede_id=sede_id,
            lugar_id=lugar_id,
            estado_ciclo_vida=estado_ciclo_vida,
            busqueda=busqueda,
            skip=skip,
            limit=limit,
        )
    )
    return {
        "status": "success",
        "data": [_a_response_con_nombres(activo).model_dump() for activo in listado.items],
        "meta": {"total": listado.total, "skip": listado.skip, "limit": listado.limit},
    }


@router.get(
    "/{id_activo}",
    summary="Obtiene un activo por id",
    responses={404: {"description": "El activo no existe"}},
)
async def obtener_activo(
    id_activo: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerActivoService, Depends(get_obtener_activo_service)],
):
    activo = await service.ejecutar(id_activo)
    return {"status": "success", "data": _a_response_con_nombres(activo).model_dump()}


@router.get(
    "/{id_activo}/historial",
    summary="Obtiene el historial de cambios de un activo",
    responses={404: {"description": "El activo no existe"}},
)
async def obtener_historial_activo(
    id_activo: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[
        ObtenerHistorialActivoService, Depends(get_obtener_historial_activo_service)
    ],
):
    entradas = await service.ejecutar(id_activo)
    return {
        "status": "success",
        "data": [EntradaHistorialResponse(**entrada.__dict__).model_dump() for entrada in entradas],
    }


@router.put(
    "/{id_activo}",
    summary="Actualiza los datos de un activo",
    responses={404: {"description": "El activo no existe"}},
)
async def actualizar_activo(
    id_activo: str,
    body: ActualizarActivoRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ActualizarActivoService, Depends(get_actualizar_activo_service)],
):
    complementos = (
        [_a_complemento_dto(c) for c in body.complementos]
        if body.complementos is not None
        else None
    )
    activo = await service.ejecutar(
        ActualizarActivoDTO(
            id_activo=id_activo,
            nombre=body.nombre,
            marca=body.marca,
            modelo=body.modelo,
            serie=body.serie,
            descripcion=body.descripcion,
            categoria_id=body.categoria_id,
            area_id=body.area_id,
            responsable_id=body.responsable_id,
            condicion_id=body.condicion_id,
            sede_id=body.sede_id,
            lugar_id=body.lugar_id,
            complementos=complementos,
            observaciones=body.observaciones,
            foto_url=body.foto_url,
            ficha_tecnica_url=body.ficha_tecnica_url,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": _a_response(activo).model_dump()}


@router.put(
    "/{id_activo}/estado",
    summary="Cambia el estado de ciclo de vida de un activo",
    responses={
        404: {"description": "El activo no existe"},
        422: {"description": "La transicion de estado no es valida"},
    },
)
async def cambiar_estado_activo(
    id_activo: str,
    body: CambiarEstadoActivoRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[CambiarEstadoActivoService, Depends(get_cambiar_estado_activo_service)],
):
    activo = await service.ejecutar(
        CambiarEstadoActivoDTO(
            id_activo=id_activo,
            estado_nuevo=body.estado_nuevo,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": _a_response(activo).model_dump()}


@router.put(
    "/{id_activo}/foto",
    summary="Sube o reemplaza la foto de un activo",
    responses={
        400: {"description": "No es una imagen JPEG, PNG o WebP, o supera 5 MB"},
        404: {"description": "El activo no existe"},
    },
)
async def subir_foto_activo(
    id_activo: str,
    request: Request,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[SubirFotoActivoService, Depends(get_subir_foto_activo_service)],
):
    # El cuerpo es la imagen en bruto. Se rechaza por el tamano declarado antes de leerlo.
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > TAMANO_MAXIMO_FOTO_BYTES:
        raise FotoDemasiadoGrandeError()

    await service.ejecutar(
        SubirFotoActivoDTO(
            id_activo=id_activo,
            contenido=await request.body(),
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "message": "Foto guardada exitosamente."}


@router.get(
    "/{id_activo}/foto",
    summary="Descarga la foto de un activo",
    responses={404: {"description": "El activo no tiene foto"}},
)
async def obtener_foto_activo(
    id_activo: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerFotoActivoService, Depends(get_obtener_foto_activo_service)],
):
    foto = await service.ejecutar(id_activo)
    return Response(
        content=foto.contenido,
        media_type=foto.tipo_mime,
        headers={"Cache-Control": "private, max-age=300", "Content-Disposition": "inline"},
    )


@router.delete(
    "/{id_activo}/foto",
    summary="Elimina la foto de un activo",
    responses={404: {"description": "El activo no existe"}},
)
async def eliminar_foto_activo(
    id_activo: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[EliminarFotoActivoService, Depends(get_eliminar_foto_activo_service)],
):
    await service.ejecutar(
        EliminarFotoActivoDTO(
            id_activo=id_activo,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "message": "Foto eliminada exitosamente."}
