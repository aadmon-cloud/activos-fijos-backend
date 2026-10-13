from datetime import datetime

from pydantic import BaseModel, Field

from modules.auditorias.domain.entities import EstadoAuditoria, ResultadoVerificacion


class IniciarAuditoriaRequest(BaseModel):
    usuario_auditado_id: str


_OBSERVACION_MAXIMA = 1000


class VerificarItemAuditoriaRequest(BaseModel):
    resultado: ResultadoVerificacion
    observacion: str | None = Field(default=None, max_length=_OBSERVACION_MAXIMA)


class ItemAuditoriaResponse(BaseModel):
    activo_id: str
    nombre: str
    numero_inventario: str
    tipo: str
    descripcion: str | None
    serie: str | None
    estado_ciclo_vida_al_inicio: str
    resultado: ResultadoVerificacion | None
    observacion: str | None
    verificado_en: datetime | None


class AuditoriaResponse(BaseModel):
    id: str
    usuario_auditado_id: str
    estado: EstadoAuditoria
    items: list[ItemAuditoriaResponse]
    fecha_inicio: datetime
    fecha_cierre: datetime | None
    pdf_archivo_id: str | None
    detalle_error_notificacion: str | None
    auditor_id: str
    auditor_nombre: str
    total: int
    encontrados: int
    encontrados_con_novedad: int
    no_encontrados: int
    pendientes: int


class AuditoriaConNombresResponse(AuditoriaResponse):
    usuario_nombre: str | None
    usuario_identificacion: str | None
    usuario_email: str | None
