from dataclasses import dataclass


@dataclass(frozen=True)
class IdentidadUsuarioAutenticada:
    id_usuario: str
    email: str
    nombre: str
    rol: str
    area_id: str | None = None


@dataclass(frozen=True)
class EstadoUsuario:
    activo: bool
    rol: str
    area_id: str | None = None
