from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from modules.usuarios.application.dto.actualizar_usuario_dto import ActualizarUsuarioDTO
from modules.usuarios.application.dto.desactivar_usuario_dto import DesactivarUsuarioDTO
from modules.usuarios.application.dto.listar_usuarios_dto import ListarUsuariosDTO
from modules.usuarios.application.dto.login_dto import LoginDTO
from modules.usuarios.application.dto.registrar_usuario_dto import RegistrarUsuarioDTO
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.domain.entities import RolUsuario
from modules.usuarios.infrastructure.api.dependencies import (
    get_actualizar_usuario_service,
    get_autenticar_usuario_service,
    get_desactivar_usuario_service,
    get_listar_usuarios_service,
    get_obtener_usuario_service,
    get_registrar_usuario_service,
)
from modules.usuarios.infrastructure.api.schemas import (
    ActualizarUsuarioRequest,
    LoginRequest,
    RegistrarUsuarioRequest,
    TokenResponse,
    UsuarioResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

_requiere_administrador_general = requiere_rol(RolUsuario.ADMINISTRADOR_GENERAL.value)


# Rutas de autenticacion


@router.post(
    "/login",
    summary="Autentica un usuario y emite un token de acceso",
    responses={401: {"description": "Credenciales invalidas"}},
)
async def login(
    body: LoginRequest,
    service: Annotated[AutenticarUsuarioService, Depends(get_autenticar_usuario_service)],
):
    token = await service.ejecutar(LoginDTO(email=body.email, password=body.password))
    return {
        "status": "success",
        "data": TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            usuario=UsuarioResponse(**token.usuario.__dict__),
        ).model_dump(),
    }


@router.get(
    "/me",
    summary="Obtiene el perfil del usuario autenticado",
)
async def obtener_mi_perfil(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[ObtenerUsuarioService, Depends(get_obtener_usuario_service)],
):
    usuario = await service.ejecutar(identidad.id_usuario)
    return {"status": "success", "data": UsuarioResponse(**usuario.__dict__).model_dump()}


# Rutas de coleccion


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registra un nuevo usuario",
    responses={
        409: {"description": "El email o la identificacion ya estan registrados"},
        422: {"description": "Datos de entrada invalidos"},
    },
)
async def registrar_usuario(
    body: RegistrarUsuarioRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[RegistrarUsuarioService, Depends(get_registrar_usuario_service)],
):
    usuario = await service.ejecutar(
        RegistrarUsuarioDTO(
            email=body.email,
            nombre=body.nombre,
            apellido=body.apellido,
            password=body.password,
            rol=body.rol,
            area_id=body.area_id,
            telefono=body.telefono,
            identificacion=body.identificacion,
            creado_por_id=identidad.id_usuario,
            creado_por_nombre=identidad.nombre,
        )
    )
    return {
        "status": "success",
        "message": "Usuario registrado exitosamente.",
        "data": {"id": usuario.id},
    }


@router.get(
    "",
    summary="Lista los usuarios existentes",
)
async def listar_usuarios(
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ListarUsuariosService, Depends(get_listar_usuarios_service)],
    busqueda: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    usuarios = await service.ejecutar(
        ListarUsuariosDTO(busqueda=busqueda, skip=skip, limit=limit)
    )
    return {
        "status": "success",
        "data": [UsuarioResponse(**usuario.__dict__).model_dump() for usuario in usuarios],
    }


# Rutas de recurso


@router.get(
    "/{id_usuario}",
    summary="Obtiene un usuario por id",
    responses={404: {"description": "El usuario no existe"}},
)
async def obtener_usuario(
    id_usuario: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ObtenerUsuarioService, Depends(get_obtener_usuario_service)],
):
    usuario = await service.ejecutar(id_usuario)
    return {"status": "success", "data": UsuarioResponse(**usuario.__dict__).model_dump()}


@router.put(
    "/{id_usuario}",
    summary="Actualiza los datos de un usuario",
    responses={404: {"description": "El usuario no existe"}},
)
async def actualizar_usuario(
    id_usuario: str,
    body: ActualizarUsuarioRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ActualizarUsuarioService, Depends(get_actualizar_usuario_service)],
):
    usuario = await service.ejecutar(
        ActualizarUsuarioDTO(
            id_usuario=id_usuario,
            nombre=body.nombre,
            apellido=body.apellido,
            rol=body.rol,
            area_id=body.area_id,
            telefono=body.telefono,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "data": UsuarioResponse(**usuario.__dict__).model_dump()}


@router.delete(
    "/{id_usuario}",
    summary="Desactiva un usuario",
    responses={404: {"description": "El usuario no existe"}},
)
async def desactivar_usuario(
    id_usuario: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[DesactivarUsuarioService, Depends(get_desactivar_usuario_service)],
):
    await service.ejecutar(
        DesactivarUsuarioDTO(
            id_usuario=id_usuario,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "message": "Usuario desactivado exitosamente."}
