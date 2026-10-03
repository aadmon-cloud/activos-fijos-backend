from dataclasses import dataclass

from modules.usuarios.domain.entities import RolUsuario


@dataclass
class ActualizarUsuarioDTO:
    id_usuario: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    apellido: str | None = None
    rol: RolUsuario | None = None
    area_id: str | None = None
    telefono: str | None = None
