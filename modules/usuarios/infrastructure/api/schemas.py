from pydantic import BaseModel, EmailStr, Field

from modules.usuarios.domain.entities import RolUsuario


class RegistrarUsuarioRequest(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    rol: RolUsuario
    area_id: str | None = None
    telefono: str | None = None
    identificacion: str | None = Field(default=None, max_length=50)


class ActualizarUsuarioRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=100)
    rol: RolUsuario | None = None
    area_id: str | None = None
    telefono: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UsuarioResponse(BaseModel):
    id: str
    email: str
    nombre: str
    apellido: str
    rol: str
    area_id: str | None
    telefono: str | None
    identificacion: str | None
    activo: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse
