from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResumenActivos:
    total: int
    por_estado_ciclo_vida: dict[str, int]
    por_tipo: dict[str, int]


@dataclass(frozen=True)
class ResumenSolicitudes:
    total: int
    por_estado: dict[str, int]
    por_tipo: dict[str, int]
    pendientes: int


@dataclass(frozen=True)
class ResumenMantenimientos:
    total: int
    por_estado: dict[str, int]
    pendientes_de_alerta: int


@dataclass(frozen=True)
class AuditoriaReciente:
    id: str
    usuario_auditado_id: str
    usuario_auditado_nombre: str | None
    fecha_cierre: datetime | None
    no_encontrados: int


@dataclass(frozen=True)
class ResumenAuditorias:
    total: int
    por_estado: dict[str, int]
    ultimas: list[AuditoriaReciente]


@dataclass(frozen=True)
class ResumenMovimientos:
    total: int
    por_tipo: dict[str, int]
    por_estado: dict[str, int]
    pendientes_de_aprobacion: int


@dataclass(frozen=True)
class ResumenDashboard:
    activos: ResumenActivos
    solicitudes: ResumenSolicitudes
    mantenimientos: ResumenMantenimientos
    auditorias: ResumenAuditorias
    movimientos: ResumenMovimientos
