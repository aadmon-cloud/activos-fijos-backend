from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from modules.movimientos.application.dto.registrar_entrada_multiple import (
    TIPOS_ORIGEN_VALIDOS,
)


class RegistrarEntradaRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    tipo_origen: str | None = None
    origen_nombre: str | None = None
    ubicacion: str | None = None
    notas: str | None = None


class RegistrarSalidaRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)
    motivo: str | None = None
    cliente_destino: str | None = None
    notas: str | None = None


class ItemEntradaMultipleRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str | None = None


class RegistrarEntradaMultipleRequest(BaseModel):
    productos: list[ItemEntradaMultipleRequest] = Field(min_length=1)
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


class ItemSalidaMultipleRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)


class RegistrarSalidaMultipleRequest(BaseModel):
    productos: list[ItemSalidaMultipleRequest] = Field(min_length=1)
    motivo: str = Field(min_length=1)
    cliente_destino: str | None = None
    notas: str | None = None


class ItemSalidaPorMercadoRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1)


class RegistrarSalidaPorMercadoRequest(BaseModel):
    mercado_nombre: str = Field(min_length=1)
    productos: list[ItemSalidaPorMercadoRequest] = Field(min_length=1)
    cantidad: int = Field(default=1, ge=1)
    cliente_destino: str | None = None
    notas: str | None = None
    referencia: str | None = None


class ItemMovimientoResponse(BaseModel):
    producto_codigo: str
    producto_nombre: str
    cantidad: int
    ubicacion: str | None


class MovimientoResponse(BaseModel):
    id: str
    tipo: str
    modalidad: str
    producto_codigo: str | None
    producto_nombre: str | None
    cantidad: int
    motivo: str | None
    tipo_origen: str | None
    origen_nombre: str | None
    cliente_destino: str | None
    ubicacion: str | None
    ubicacion_origen: str | None
    ubicacion_destino: str | None
    notas: str | None
    remision: str | None
    caso: str | None
    referencia: str | None
    numero_cajas: int | None
    kit_nombre: str | None
    nombre_mercado: str | None
    productos: list[ItemMovimientoResponse] | None
    pdf_nombre: str | None
    usuario: str
    fecha: datetime


class MovimientosPaginadosResponse(BaseModel):
    resultado: list[MovimientoResponse]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int


class ConfirmacionReservaResponse(BaseModel):
    movimientos: list[MovimientoResponse]
    remision: str
