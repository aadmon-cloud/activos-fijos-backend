from dataclasses import dataclass


@dataclass
class ActualizarPermisosRolDTO:
    rol: str
    permisos: list[str]
    actor_id: str
    actor_nombre: str


@dataclass
class RestablecerPermisosRolDTO:
    rol: str
    actor_id: str
    actor_nombre: str
