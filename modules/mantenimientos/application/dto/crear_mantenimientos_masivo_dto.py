from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from modules.mantenimientos.domain.entities import TipoMantenimiento


@dataclass
class CrearMantenimientosMasivoDTO:
    """Un mismo mantenimiento ya realizado sobre varios activos, identificados por su codigo (numero de
    inventario)."""

    codigos: list[str]
    tipo: TipoMantenimiento
    tecnico_responsable_id: str
    fecha: datetime
    creado_por_id: str
    creado_por_nombre: str
    observaciones: str | None = None
    costo: Decimal | None = None
    frecuencia_dias: int | None = None


@dataclass
class MantenimientoRegistradoDTO:
    codigo: str
    activo_id: str
    mantenimiento_id: str


@dataclass
class ResultadoMantenimientosMasivoDTO:
    registrados: list[MantenimientoRegistradoDTO] = field(default_factory=list)
    no_encontrados: list[str] = field(default_factory=list)
