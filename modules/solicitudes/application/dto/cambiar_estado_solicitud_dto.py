from dataclasses import dataclass

from modules.solicitudes.domain.entities import EstadoSolicitud


@dataclass
class CambiarEstadoSolicitudDTO:
    id_solicitud: str
    estado_nuevo: EstadoSolicitud
    actor_id: str
    actor_nombre: str
    actor_rol: str
    actor_area_id: str | None
    comentario: str | None = None
