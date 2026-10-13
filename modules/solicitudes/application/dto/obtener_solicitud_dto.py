from dataclasses import dataclass


@dataclass
class ObtenerSolicitudDTO:
    id_solicitud: str
    actor_id: str
    actor_rol: str
    actor_area_id: str | None = None
