from dataclasses import dataclass, field

from modules.solicitudes.domain.entities import PrioridadSolicitud, TipoSolicitud


@dataclass
class CrearSolicitudDTO:
    tipo: TipoSolicitud
    activo_id: str
    descripcion: str
    prioridad: PrioridadSolicitud
    creado_por_id: str
    creado_por_nombre: str
    creado_por_rol: str
    evidencias: list[str] = field(default_factory=list)
