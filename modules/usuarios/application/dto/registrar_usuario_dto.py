from dataclasses import dataclass

from modules.usuarios.domain.entities import RolUsuario


@dataclass
class RegistrarUsuarioDTO:
    email: str
    nombre: str
    apellido: str
    password: str
    rol: RolUsuario
    creado_por_id: str
    creado_por_nombre: str
    area_id: str | None = None
    telefono: str | None = None
    identificacion: str | None = None
