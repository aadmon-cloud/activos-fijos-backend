from dataclasses import dataclass


@dataclass
class AgregarSeguimientoSolicitudDTO:
    id_solicitud: str
    comentario: str
    actor_id: str
    actor_nombre: str
    actor_rol: str
    actor_area_id: str | None
