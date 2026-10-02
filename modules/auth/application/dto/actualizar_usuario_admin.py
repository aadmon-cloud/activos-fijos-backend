from pydantic import BaseModel, Field

from modules.auth.domain.entities.usuario import RolUsuario


class ActualizarUsuarioAdminInput(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    rol: RolUsuario | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8)
