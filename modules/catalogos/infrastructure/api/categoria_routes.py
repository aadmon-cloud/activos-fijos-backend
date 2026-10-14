from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.catalogos.application.dto.actualizar_categoria_dto import ActualizarCategoriaDTO
from modules.catalogos.application.dto.crear_categoria_dto import CrearCategoriaDTO
from modules.catalogos.application.services.actualizar_categoria import (
    ActualizarCategoriaService,
)
from modules.catalogos.application.services.crear_categoria import CrearCategoriaService
from modules.catalogos.application.services.eliminar_categoria import EliminarCategoriaService
from modules.catalogos.application.services.listar_categorias import ListarCategoriasService
from modules.catalogos.application.services.obtener_categoria import ObtenerCategoriaService
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_categoria_service,
    get_crear_categoria_service,
    get_eliminar_categoria_service,
    get_listar_categorias_service,
    get_obtener_categoria_service,
)
from modules.catalogos.infrastructure.api.schemas import (
    ActualizarCategoriaRequest,
    CategoriaResponse,
    CrearCategoriaRequest,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_permiso,
    requiere_usuario_autenticado,
)


router = APIRouter(prefix="/api/categorias", tags=["categorias"])

_requiere_catalogos_crear = requiere_permiso("catalogos-crear")
_requiere_catalogos_editar = requiere_permiso("catalogos-editar")
_requiere_catalogos_eliminar = requiere_permiso("catalogos-eliminar")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva categoria",
    responses={409: {"description": "Ya existe una categoria con ese nombre"}},
)
async def crear_categoria(
    body: CrearCategoriaRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_crear)
    ],
    service: Annotated[CrearCategoriaService, Depends(get_crear_categoria_service)],
):
    categoria = await service.ejecutar(
        CrearCategoriaDTO(
            nombre=body.nombre,
            descripcion=body.descripcion,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Categoria creada exitosamente.",
        "data": {"id": categoria.id},
    }


@router.get(
    "",
    summary="Lista las categorias existentes",
)
async def listar_categorias(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ListarCategoriasService, Depends(get_listar_categorias_service)],
):
    categorias = await service.ejecutar()
    return {
        "status": "success",
        "data": [CategoriaResponse(**categoria.__dict__).model_dump() for categoria in categorias],
    }


@router.get(
    "/{id_categoria}",
    summary="Obtiene una categoria por id",
    responses={404: {"description": "La categoria no existe"}},
)
async def obtener_categoria(
    id_categoria: str,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerCategoriaService, Depends(get_obtener_categoria_service)],
):
    categoria = await service.ejecutar(id_categoria)
    return {"status": "success", "data": CategoriaResponse(**categoria.__dict__).model_dump()}


@router.put(
    "/{id_categoria}",
    summary="Actualiza los datos de una categoria",
    responses={
        404: {"description": "La categoria no existe"},
        409: {"description": "Ya existe una categoria con ese nombre"},
    },
)
async def actualizar_categoria(
    id_categoria: str,
    body: ActualizarCategoriaRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_editar)
    ],
    service: Annotated[ActualizarCategoriaService, Depends(get_actualizar_categoria_service)],
):
    categoria = await service.ejecutar(
        ActualizarCategoriaDTO(
            id_categoria=id_categoria,
            nombre=body.nombre,
            descripcion=body.descripcion,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": CategoriaResponse(**categoria.__dict__).model_dump()}


@router.delete(
    "/{id_categoria}",
    summary="Elimina una categoria",
    responses={404: {"description": "La categoria no existe"}},
)
async def eliminar_categoria(
    id_categoria: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_catalogos_eliminar)
    ],
    service: Annotated[EliminarCategoriaService, Depends(get_eliminar_categoria_service)],
):
    await service.ejecutar(id_categoria)
    return {"status": "success", "message": "Categoria eliminada exitosamente."}
