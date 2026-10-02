from pydantic import BaseModel, EmailStr, Field

from modules.auth.domain.entities.usuario import RolUsuario


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegistrarUsuarioRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    username: str | None = Field(default=None, min_length=3, max_length=50)


class UsuarioResponse(BaseModel):
    id: str
    email: str
    username: str
    rol: RolUsuario
    activo: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str


class CrearUsuarioAdminRequest(BaseModel):
    email: EmailStr
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    rol: RolUsuario = RolUsuario.OPERATIVO


class ActualizarUsuarioAdminRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    rol: RolUsuario | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UsuariosPaginadosResponse(BaseModel):
    resultado: list[UsuarioResponse]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int
