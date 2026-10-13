from dataclasses import dataclass

from modules.usuarios.domain.entities import RolUsuario


@dataclass
class RegistrarUsuarioDTO:
    email: str
    nombre: str
    apellido: str
    rol: RolUsuario
    creado_por_id: str
    creado_por_nombre: str
    area_id: str | None = None
    telefono: str | None = None
    identificacion: str | None = None

    # El ingreso es con Google: normalmente no hay contrasena. Solo se usa si se reabre el ingreso con contrasena
    # (pruebas locales).
    password: str | None = None
