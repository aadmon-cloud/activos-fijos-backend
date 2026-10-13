from datetime import datetime

from pydantic import BaseModel


class ResumenActivosResponse(BaseModel):
    total: int
    por_estado_ciclo_vida: dict[str, int]
    por_tipo: dict[str, int]


class ResumenSolicitudesResponse(BaseModel):
    total: int
    por_estado: dict[str, int]
    por_tipo: dict[str, int]
    pendientes: int


class ResumenMantenimientosResponse(BaseModel):
    total: int
    por_estado: dict[str, int]
    pendientes_de_alerta: int


class AuditoriaRecienteResponse(BaseModel):
    id: str
    usuario_auditado_id: str
    usuario_auditado_nombre: str | None
    fecha_cierre: datetime | None
    no_encontrados: int


class ResumenAuditoriasResponse(BaseModel):
    total: int
    por_estado: dict[str, int]
    ultimas: list[AuditoriaRecienteResponse]


class ResumenMovimientosResponse(BaseModel):
    total: int
    por_tipo: dict[str, int]
    por_estado: dict[str, int]
    pendientes_de_aprobacion: int


class DashboardResponse(BaseModel):
    activos: ResumenActivosResponse
    solicitudes: ResumenSolicitudesResponse
    mantenimientos: ResumenMantenimientosResponse
    auditorias: ResumenAuditoriasResponse
    movimientos: ResumenMovimientosResponse
