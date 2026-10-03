from datetime import datetime

from pydantic import BaseModel, Field

from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, TipoSolicitud


class CrearSolicitudRequest(BaseModel):
    tipo: TipoSolicitud
    activo_id: str
    descripcion: str = Field(min_length=1)
    prioridad: PrioridadSolicitud
    evidencias: list[str] = Field(default_factory=list)


class CambiarEstadoSolicitudRequest(BaseModel):
    estado_nuevo: EstadoSolicitud
    comentario: str | None = None


class AgregarSeguimientoSolicitudRequest(BaseModel):
    comentario: str = Field(min_length=1)


class EntradaSeguimientoResponse(BaseModel):
    autor_nombre: str
    autor_fecha: datetime
    comentario: str
    estado_anterior: str | None
    estado_nuevo: str | None


class SolicitudResponse(BaseModel):
    id: str
    tipo: str
    activo_id: str
    descripcion: str
    prioridad: str
    evidencias: list[str]
    estado: str
    rol_asignado: str | None
    area_id: str | None
    seguimiento: list[EntradaSeguimientoResponse]
