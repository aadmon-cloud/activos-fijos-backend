from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from modules.movimientos.application.dto.registrar_entrada_multiple import (
    TIPOS_ORIGEN_VALIDOS,
)


class ProponerEntradaRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    tipo_origen: str | None = None
    origen_nombre: str | None = None
    ubicacion: str | None = None
    notas: str | None = None


class ProponerSalidaRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)
    motivo: str | None = None
    cliente_destino: str | None = None
    notas: str | None = None


class ItemProponerEntradaMultipleRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str | None = None


class ProponerEntradaMultipleRequest(BaseModel):
    productos: list[ItemProponerEntradaMultipleRequest] = Field(min_length=1)
    tipo_origen: str
    origen_nombre: str = Field(min_length=1)
    ubicacion: str | None = None
    notas: str | None = None

    @field_validator("tipo_origen")
    @classmethod
    def _validar_tipo_origen(cls, v: str) -> str:
        v_normalizado = v.lower()
        if v_normalizado not in TIPOS_ORIGEN_VALIDOS:
            raise ValueError(
                f"tipo_origen debe ser uno de: {', '.join(sorted(TIPOS_ORIGEN_VALIDOS))}"
            )
        return v_normalizado


class ItemProponerSalidaMultipleRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)


class ProponerSalidaMultipleRequest(BaseModel):
    productos: list[ItemProponerSalidaMultipleRequest] = Field(min_length=1)
    motivo: str = Field(min_length=1)
    cliente_destino: str | None = None
    notas: str | None = None


class EliminarMovimientosPendientesMultiplesRequest(BaseModel):
    movimientos_pendientes_ids: list[str] = Field(min_length=1)


class MovimientoPendienteResponse(BaseModel):
    id: str
    tipo_propuesto: str
    payload: dict
    estado: str
    movimiento_id: str | None
    propuesto_por: str
    fecha_propuesta: datetime
    confirmado_por: str | None
    fecha_confirmacion: datetime | None


class MovimientosPendientesPaginadosResponse(BaseModel):
    resultado: list[MovimientoPendienteResponse]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int


class EliminarMovimientosPendientesMultiplesResponse(BaseModel):
    eliminadas: int
    total_solicitadas: int
