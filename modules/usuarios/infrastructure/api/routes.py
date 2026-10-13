from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from modules.usuarios.application.dto.actualizar_usuario_dto import ActualizarUsuarioDTO
from modules.usuarios.application.dto.cambiar_password_dto import CambiarPasswordDTO
from modules.usuarios.application.dto.desactivar_usuario_dto import DesactivarUsuarioDTO
from modules.usuarios.application.dto.listar_usuarios_dto import ListarUsuariosDTO
from modules.usuarios.application.dto.login_dto import LoginDTO
from modules.usuarios.application.dto.login_google_dto import LoginGoogleDTO
from modules.usuarios.application.dto.reactivar_usuario_dto import ReactivarUsuarioDTO
from modules.usuarios.application.dto.registrar_usuario_dto import RegistrarUsuarioDTO
from modules.usuarios.application.dto.restablecer_password_dto import RestablecerPasswordDTO
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_con_google import AutenticarConGoogleService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.cambiar_password import CambiarPasswordService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_directorio_usuarios import (
    ListarDirectorioUsuariosService,
)
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.reactivar_usuario import ReactivarUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.application.services.restablecer_password import RestablecerPasswordService
from modules.usuarios.domain.entities import RolUsuario
from modules.usuarios.infrastructure.api.dependencies import (
    get_actualizar_usuario_service,
    get_autenticar_con_google_service,
    get_autenticar_usuario_service,
    get_cambiar_password_service,
    get_desactivar_usuario_service,
    get_listar_directorio_usuarios_service,
    get_listar_usuarios_service,
    get_obtener_usuario_service,
    get_reactivar_usuario_service,
    get_registrar_usuario_service,
    get_restablecer_password_service,
    requiere_login_password_habilitado,
)
from modules.usuarios.infrastructure.api.schemas import (
    ActualizarUsuarioRequest,
    CambiarPasswordRequest,
    LoginGoogleRequest,
    LoginRequest,
    RegistrarUsuarioRequest,
    RestablecerPasswordRequest,
    SesionResponse,
    UsuarioResponse,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.session_cookie import (
    eliminar_cookie_sesion,
    establecer_cookie_sesion,
)
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

_requiere_administrador_general = requiere_rol(RolUsuario.ADMINISTRADOR_GENERAL.value)


# Rutas de autenticacion


@router.post(
    "/login/google",
    summary="Abre la sesion (cookie HttpOnly) con la cuenta de Google de un usuario ya registrado",
    responses={
        401: {"description": "Token de Google invalido, o la cuenta no tiene acceso al sistema"},
        502: {"description": "El ingreso con Google no esta configurado"},
    },
)
async def login_con_google(
    body: LoginGoogleRequest,
    response: Response,
    service: Annotated[AutenticarConGoogleService, Depends(get_autenticar_con_google_service)],
):
    token = await service.ejecutar(LoginGoogleDTO(credencial=body.credencial, nonce=body.nonce))
    establecer_cookie_sesion(response, token.access_token)
    return {
        "status": "success",
        "data": SesionResponse(usuario=UsuarioResponse(**token.usuario.__dict__)).model_dump(),
    }


@router.post(
    "/login",
    summary="Ingreso con contrasena: deshabilitado salvo que se reabra para pruebas locales",
    dependencies=[Depends(requiere_login_password_habilitado)],
    responses={
        401: {"description": "Credenciales invalidas"},
        403: {"description": "El ingreso con contrasena esta deshabilitado"},
    },
)
async def login(
    body: LoginRequest,
    response: Response,
    service: Annotated[AutenticarUsuarioService, Depends(get_autenticar_usuario_service)],
):
    token = await service.ejecutar(LoginDTO(email=body.email, password=body.password))
    establecer_cookie_sesion(response, token.access_token)
    return {
        "status": "success",
        "data": SesionResponse(usuario=UsuarioResponse(**token.usuario.__dict__)).model_dump(),
    }


@router.post(
    "/logout",
    summary="Cierra la sesion eliminando la cookie",
)
async def logout(response: Response):
    eliminar_cookie_sesion(response)
    return {"status": "success", "message": "Sesion cerrada exitosamente."}


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


@router.put(
    "/me/password",
    summary="Cambia la contrasena del usuario autenticado",
    responses={
        400: {"description": "La contrasena actual es incorrecta o la nueva es debil"},
        422: {"description": "La contrasena nueva es igual a la actual"},
    },
)
async def cambiar_mi_password(
    body: CambiarPasswordRequest,
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[CambiarPasswordService, Depends(get_cambiar_password_service)],
):
    await service.ejecutar(
        CambiarPasswordDTO(
            id_usuario=identidad.id_usuario,
            password_actual=body.password_actual,
            password_nueva=body.password_nueva,
        )
    )
    return {"status": "success", "message": "Contrasena actualizada exitosamente."}


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


@router.get(
    "/directorio",
    summary="Directorio de personas activas (nombre solamente) para elegir a quien se le presta un activo",
)
async def listar_directorio_usuarios(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    service: Annotated[
        ListarDirectorioUsuariosService, Depends(get_listar_directorio_usuarios_service)
    ],
    busqueda: str | None = Query(default=None, max_length=100),
):
    usuarios = await service.ejecutar(busqueda=busqueda)
    return {
        "status": "success",
        "data": [{"id": u.id, "nombre": u.nombre, "apellido": u.apellido} for u in usuarios],
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


@router.post(
    "/{id_usuario}/reactivar",
    summary="Reactiva un usuario desactivado",
    responses={404: {"description": "El usuario no existe"}},
)
async def reactivar_usuario(
    id_usuario: str,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[ReactivarUsuarioService, Depends(get_reactivar_usuario_service)],
):
    await service.ejecutar(
        ReactivarUsuarioDTO(
            id_usuario=id_usuario,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "message": "Usuario reactivado exitosamente."}


@router.put(
    "/{id_usuario}/password",
    summary="Restablece la contrasena de un usuario",
    responses={
        400: {"description": "La contrasena nueva es debil"},
        404: {"description": "El usuario no existe"},
    },
)
async def restablecer_password(
    id_usuario: str,
    body: RestablecerPasswordRequest,
    identidad: Annotated[
        IdentidadUsuarioAutenticada, Depends(_requiere_administrador_general)
    ],
    service: Annotated[RestablecerPasswordService, Depends(get_restablecer_password_service)],
):
    await service.ejecutar(
        RestablecerPasswordDTO(
            id_usuario=id_usuario,
            password_nueva=body.password_nueva,
            actualizado_por_id=identidad.id_usuario,
            actualizado_por_nombre=identidad.nombre,
        )
    )
    return {"status": "success", "message": "Contrasena restablecida exitosamente."}
