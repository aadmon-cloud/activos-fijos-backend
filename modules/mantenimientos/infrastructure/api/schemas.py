from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from modules.mantenimientos.application.services.registrar_mantenimientos_masivo import (
    LIMITE_CODIGOS_MASIVO,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, TipoMantenimiento

_OBSERVACIONES_MAXIMO = 2000
_CODIGO_MAXIMO = 50


class CrearMantenimientoRequest(BaseModel):
    activo_id: str
    tipo: TipoMantenimiento
    tecnico_responsable_id: str
    fecha: datetime
    solicitud_id: str | None = None
    observaciones: str | None = Field(default=None, max_length=_OBSERVACIONES_MAXIMO)
    costo: Decimal | None = Field(default=None, ge=0)
    frecuencia_dias: int | None = Field(default=None, ge=1)


class CrearMantenimientosMasivoRequest(BaseModel):
    codigos: list[Annotated[str, Field(max_length=_CODIGO_MAXIMO)]] = Field(
        min_length=1, max_length=LIMITE_CODIGOS_MASIVO
    )
    tipo: TipoMantenimiento
    tecnico_responsable_id: str
    fecha: datetime
    observaciones: str | None = Field(default=None, max_length=_OBSERVACIONES_MAXIMO)
    costo: Decimal | None = Field(default=None, ge=0)
    frecuencia_dias: int | None = Field(default=None, ge=1)


class CambiarEstadoMantenimientoRequest(BaseModel):
    estado_nuevo: EstadoMantenimiento


class ArchivoMantenimientoResponse(BaseModel):
    archivo_id: str
    nombre: str


class MantenimientoResponse(BaseModel):
    id: str
    activo_id: str
    solicitud_id: str | None
    tipo: str
    tecnico_responsable_id: str
    fecha: datetime
    observaciones: str | None
    costo: Decimal | None
    documentos: list[ArchivoMantenimientoResponse]
    evidencias: list[ArchivoMantenimientoResponse]
    estado: str
    frecuencia_dias: int | None
    proxima_fecha_sugerida: datetime | None
    alerta_enviada: bool
    creado_por_id: str
    creado_por_nombre: str
    fecha_creacion: datetime


class MantenimientoConNombresResponse(MantenimientoResponse):
    activo_nombre: str | None
    activo_numero_inventario: str | None
    tecnico_nombre: str | None

    # Estados a los que puede pasar ahora (los decide el backend).
    estados_permitidos: list[str]
