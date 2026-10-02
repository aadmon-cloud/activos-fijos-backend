from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse

from config.settings import settings
from modules.auth.application.dto.actualizar_usuario_admin import (
    ActualizarUsuarioAdminInput,
)
from modules.auth.application.dto.cambiar_password import CambiarPasswordInput
from modules.auth.application.dto.crear_usuario_admin import CrearUsuarioAdminInput
from modules.auth.application.dto.listar_usuarios import ListarUsuariosInput
from modules.auth.application.dto.login import LoginInput
from modules.auth.application.dto.registrar_usuario import RegistrarUsuarioInput
from modules.auth.application.dto.restablecer_password import RestablecerPasswordInput
from modules.auth.application.dto.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordInput,
)
from modules.auth.application.services.actualizar_usuario_admin import (
    ActualizarUsuarioAdminService,
)
from modules.auth.application.services.cambiar_password import CambiarPasswordService
from modules.auth.application.services.crear_usuario_admin import (
    CrearUsuarioAdminService,
)
from modules.auth.application.services.eliminar_usuario_admin import (
    EliminarUsuarioAdminService,
)
from modules.auth.application.services.iniciar_login_google import (
    IniciarLoginGoogleService,
)
from modules.auth.application.services.listar_usuarios import ListarUsuariosService
from modules.auth.application.services.login import LoginService
from modules.auth.application.services.login_con_google import LoginConGoogleService
from modules.auth.application.services.registrar_usuario import RegistrarUsuarioService
from modules.auth.application.services.restablecer_password import (
    RestablecerPasswordService,
)
from modules.auth.application.services.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordService,
)
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.infrastructure.api.dependencies import (
    get_actualizar_usuario_admin_service,
    get_cambiar_password_service,
    get_crear_usuario_admin_service,
    get_eliminar_usuario_admin_service,
    get_iniciar_login_google_service,
    get_listar_usuarios_input,
    get_listar_usuarios_service,
    get_login_con_google_service,
    get_login_service,
    get_registrar_usuario_service,
    get_restablecer_password_service,
    get_solicitar_recuperacion_password_service,
)
from modules.auth.infrastructure.api.schemas import (
    ActualizarUsuarioAdminRequest,
    ChangePasswordRequest,
    CrearUsuarioAdminRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegistrarUsuarioRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsuarioResponse,
    UsuariosPaginadosResponse,
)
from shared.infrastructure.api.dependencies.auth import (
    require_authenticated,
    require_super_admin,
)

router = APIRouter(prefix="/api/auth", tags=["autenticacion"])

_MENSAJE_RECUPERACION_GENERICO = (
    "Si el email está registrado, recibirás un enlace de recuperación."
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica un usuario y emite un token",
    responses={
        401: {"description": "Email o contraseña incorrectos"},
        403: {"description": "Usuario desactivado"},
    },
)
async def login(
    payload: LoginRequest,
    service: Annotated[LoginService, Depends(get_login_service)],
) -> TokenResponse:
    resultado = await service.ejecutar(
        LoginInput(email=str(payload.email), password=payload.password)
    )
    return TokenResponse(
        access_token=resultado.access_token,
        token_type=resultado.token_type,
        usuario=UsuarioResponse.model_validate(resultado.usuario.model_dump()),
    )


@router.post(
    "/registro",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra un nuevo usuario con rol operativo",
    responses={
        400: {"description": "Las contraseñas no coinciden"},
        409: {"description": "El email ya está registrado"},
    },
)
async def registrar_usuario(
    payload: RegistrarUsuarioRequest,
    service: Annotated[RegistrarUsuarioService, Depends(get_registrar_usuario_service)],
) -> UsuarioResponse:
    usuario = await service.ejecutar(
        RegistrarUsuarioInput(
            email=str(payload.email),
            password=payload.password,
            confirm_password=payload.confirm_password,
            username=payload.username,
        )
    )
    return UsuarioResponse.model_validate(usuario.model_dump())


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Devuelve el usuario autenticado actual (a partir del Bearer token)",
)
async def obtener_usuario_actual(
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario_actual.model_dump())


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Solicita la recuperación de password",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    service: Annotated[
        SolicitarRecuperacionPasswordService,
        Depends(get_solicitar_recuperacion_password_service),
    ],
) -> MessageResponse:
    await service.ejecutar(SolicitarRecuperacionPasswordInput(email=str(payload.email)))
    return MessageResponse(message=_MENSAJE_RECUPERACION_GENERICO)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Restablece el password usando un token de recuperación",
    responses={
        400: {"description": "Token inválido/expirado o las contraseñas no coinciden"},
    },
)
async def reset_password(
    payload: ResetPasswordRequest,
    service: Annotated[RestablecerPasswordService, Depends(get_restablecer_password_service)],
) -> MessageResponse:
    await service.ejecutar(
        RestablecerPasswordInput(
            token=payload.token,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        )
    )
    return MessageResponse(message="Contraseña actualizada exitosamente.")


@router.get(
    "/google",
    summary="Inicia el login con Google (redirige a la pantalla de consentimiento)",
    responses={
        500: {"description": "Google OAuth no está configurado en el servidor"},
    },
)
async def google_login(
    service: Annotated[IniciarLoginGoogleService, Depends(get_iniciar_login_google_service)],
) -> RedirectResponse:
    url_autorizacion = service.ejecutar()
    return RedirectResponse(url=url_autorizacion)


@router.get(
    "/google/callback",
    summary="Callback de Google OAuth: crea/enlaza el usuario y redirige al frontend con el token",
    responses={
        403: {"description": "Usuario desactivado"},
        500: {"description": "Google OAuth no está configurado en el servidor"},
        502: {"description": "Falla el intercambio con Google"},
    },
)
async def google_callback(
    code: str,
    service: Annotated[LoginConGoogleService, Depends(get_login_con_google_service)],
) -> RedirectResponse:
    resultado = await service.ejecutar(code)
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google-callback?token={resultado.access_token}"
    )
    return RedirectResponse(url=redirect_url)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Cambia el password del usuario autenticado",
    responses={
        400: {"description": "Las contraseñas no coinciden"},
        401: {"description": "La contraseña actual es incorrecta"},
    },
)
async def change_password(
    payload: ChangePasswordRequest,
    usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[CambiarPasswordService, Depends(get_cambiar_password_service)],
) -> MessageResponse:
    await service.ejecutar(
        usuario_actual,
        CambiarPasswordInput(
            current_password=payload.current_password,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        ),
    )
    return MessageResponse(message="Contraseña actualizada exitosamente.")


@router.get(
    "/usuarios",
    response_model=UsuariosPaginadosResponse,
    summary="Lista usuarios paginados (solo super_admin)",
)
async def listar_usuarios(
    _admin: Annotated[Usuario, Depends(require_super_admin)],
    entrada: Annotated[ListarUsuariosInput, Depends(get_listar_usuarios_input)],
    service: Annotated[ListarUsuariosService, Depends(get_listar_usuarios_service)],
) -> UsuariosPaginadosResponse:
    resultado = await service.ejecutar(entrada)
    return UsuariosPaginadosResponse(
        resultado=[
            UsuarioResponse.model_validate(usuario.model_dump())
            for usuario in resultado.resultado
        ],
        pagina_actual=resultado.pagina_actual,
        elementos_por_pagina=resultado.elementos_por_pagina,
        total_elementos=resultado.total_elementos,
        total_paginas=resultado.total_paginas,
    )


@router.post(
    "/usuarios",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un usuario con rol explícito (solo super_admin)",
    responses={
        409: {"description": "El email ya está registrado"},
    },
)
async def crear_usuario_admin(
    payload: CrearUsuarioAdminRequest,
    admin_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[CrearUsuarioAdminService, Depends(get_crear_usuario_admin_service)],
) -> UsuarioResponse:
    usuario = await service.ejecutar(
        admin_actual,
        CrearUsuarioAdminInput(
            email=str(payload.email),
            username=payload.username,
            password=payload.password,
            rol=payload.rol,
        ),
    )
    return UsuarioResponse.model_validate(usuario.model_dump())


@router.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResponse,
    summary="Actualiza un usuario existente (solo super_admin)",
    responses={
        400: {"description": "No puedes operar sobre tu propio usuario por esta vía"},
        404: {"description": "No existe un usuario con ese id"},
    },
)
async def actualizar_usuario_admin(
    usuario_id: str,
    payload: ActualizarUsuarioAdminRequest,
    admin_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        ActualizarUsuarioAdminService, Depends(get_actualizar_usuario_admin_service)
    ],
) -> UsuarioResponse:
    usuario = await service.ejecutar(
        admin_actual,
        usuario_id,
        ActualizarUsuarioAdminInput(
            username=payload.username,
            rol=payload.rol,
            activo=payload.activo,
            password=payload.password,
        ),
    )
    return UsuarioResponse.model_validate(usuario.model_dump())


@router.delete(
    "/usuarios/{usuario_id}",
    response_model=MessageResponse,
    summary="Elimina un usuario (solo super_admin)",
    responses={
        400: {"description": "No puedes operar sobre tu propio usuario por esta vía"},
        404: {"description": "No existe un usuario con ese id"},
    },
)
async def eliminar_usuario_admin(
    usuario_id: str,
    admin_actual: Annotated[Usuario, Depends(require_super_admin)],
    service: Annotated[
        EliminarUsuarioAdminService, Depends(get_eliminar_usuario_admin_service)
    ],
) -> MessageResponse:
    await service.ejecutar(admin_actual, usuario_id)
    return MessageResponse(message="Usuario eliminado exitosamente.")
