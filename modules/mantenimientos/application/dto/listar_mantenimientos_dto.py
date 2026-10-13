from dataclasses import dataclass

from modules.mantenimientos.domain.entities import EstadoMantenimiento, TipoMantenimiento


@dataclass
class ListarMantenimientosDTO:
    activo_id: str | None = None
    tecnico_responsable_id: str | None = None
    estado: EstadoMantenimiento | None = None
    tipo: TipoMantenimiento | None = None
    solicitud_id: str | None = None
    skip: int = 0
    limit: int = 100
