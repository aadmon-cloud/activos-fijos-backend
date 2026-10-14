from pydantic import BaseModel, EmailStr, Field

from modules.usuarios.domain.entities import RolUsuario


class RegistrarUsuarioRequest(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    rol: RolUsuario
    area_id: str | None = None
    telefono: str | None = None
    identificacion: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, min_length=8)


class ActualizarUsuarioRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=100)
    rol: RolUsuario | None = None
    area_id: str | None = None
    telefono: str | None = None


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8)


class RestablecerPasswordRequest(BaseModel):
    password_nueva: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginGoogleRequest(BaseModel):
    # Token de identidad (JWT) que Google entrega al navegador y el nonce con el que se pidio.
    credencial: str = Field(min_length=20, max_length=4096)
    nonce: str = Field(min_length=8, max_length=200)


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


class UsuarioSesionResponse(UsuarioResponse):
    # Funciones habilitadas para su rol en la matriz de permisos: el frontend las usa para mostrar u ocultar opciones.
    permisos: list[str]


class SesionResponse(BaseModel):
    usuario: UsuarioSesionResponse
