from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from modules.mantenimientos.domain.entities import TipoMantenimiento


@dataclass
class CrearMantenimientoDTO:
    activo_id: str
    tipo: TipoMantenimiento
    tecnico_responsable_id: str
    fecha: datetime
    creado_por_id: str
    creado_por_nombre: str
    solicitud_id: str | None = None
    observaciones: str | None = None
    costo: Decimal | None = None
    frecuencia_dias: int | None = None
