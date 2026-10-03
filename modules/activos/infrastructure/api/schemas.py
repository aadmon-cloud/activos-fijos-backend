from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from modules.activos.domain.entities import EstadoCicloVida, TipoActivo


class ComplementoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    cantidad: int = Field(default=1, ge=1)
    serie: str | None = None


class ComplementoResponse(BaseModel):
    nombre: str
    descripcion: str | None
    cantidad: int
    serie: str | None


class CrearActivoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    numero_inventario: str = Field(min_length=1, max_length=50)
    tipo: TipoActivo
    categoria_id: str
    area_id: str
    responsable_id: str
    condicion_id: str
    sede_id: str
    lugar_id: str
    valor: Decimal = Field(gt=0)
    fecha_adquisicion: datetime
    marca: str | None = None
    modelo: str | None = None
    serie: str | None = None
    descripcion: str | None = None
    complementos: list[ComplementoRequest] = Field(default_factory=list)
    observaciones: str | None = None
    foto_url: str | None = None
    ficha_tecnica_url: str | None = None


class ActualizarActivoRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    marca: str | None = None
    modelo: str | None = None
    serie: str | None = None
    descripcion: str | None = None
    categoria_id: str | None = None
    area_id: str | None = None
    responsable_id: str | None = None
    condicion_id: str | None = None
    sede_id: str | None = None
    lugar_id: str | None = None
    valor: Decimal | None = Field(default=None, gt=0)
    fecha_adquisicion: datetime | None = None
    complementos: list[ComplementoRequest] | None = None
    observaciones: str | None = None
    foto_url: str | None = None
    ficha_tecnica_url: str | None = None


class CambiarEstadoActivoRequest(BaseModel):
    estado_nuevo: EstadoCicloVida


class ActivoResponse(BaseModel):
    id: str
    nombre: str
    numero_inventario: str
    tipo: str
    marca: str | None
    modelo: str | None
    serie: str | None
    descripcion: str | None
    categoria_id: str
    area_id: str
    responsable_id: str
    condicion_id: str
    estado_ciclo_vida: str
    sede_id: str
    lugar_id: str
    valor: Decimal
    fecha_adquisicion: datetime
    complementos: list[ComplementoResponse]
    observaciones: str | None
    foto_url: str | None
    ficha_tecnica_url: str | None


class EntradaHistorialResponse(BaseModel):
    id: str
    activo_id: str
    campo: str
    valor_anterior: str
    valor_nuevo: str
    modificado_por_nombre: str
    modificado_por_fecha: datetime
