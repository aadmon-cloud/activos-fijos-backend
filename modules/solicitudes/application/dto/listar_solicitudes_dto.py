from dataclasses import dataclass

from modules.solicitudes.domain.entities import EstadoSolicitud, TipoSolicitud


@dataclass
class ListarSolicitudesDTO:
    # Quien consulta: define lo que puede ver. Siempre se informa desde la capa HTTP.
    actor_id: str
    actor_rol: str
    actor_area_id: str | None = None
    tipo: TipoSolicitud | None = None
    estado: EstadoSolicitud | None = None
    activo_id: str | None = None
    rol_asignado: str | None = None
    area_id: str | None = None
    creado_por_id: str | None = None
    skip: int = 0
    limit: int = 100
