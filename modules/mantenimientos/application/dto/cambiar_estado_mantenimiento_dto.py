from dataclasses import dataclass

from modules.mantenimientos.domain.entities import EstadoMantenimiento


@dataclass
class CambiarEstadoMantenimientoDTO:
    id_mantenimiento: str
    estado_nuevo: EstadoMantenimiento
    actor_id: str
    actor_nombre: str
    actor_rol: str
    actor_area_id: str | None
