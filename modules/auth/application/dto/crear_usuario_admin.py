from pydantic import BaseModel, Field

from modules.auth.domain.entities.usuario import RolUsuario


class CrearUsuarioAdminInput(BaseModel):
    email: str = Field(min_length=1)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    rol: RolUsuario = RolUsuario.OPERATIVO
