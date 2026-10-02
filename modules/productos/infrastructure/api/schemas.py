from pydantic import BaseModel, Field


class CrearProductoRequest(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    categoria: str | None = None
    stock_minimo: int = Field(default=0, ge=0)
    precio_unitario: float = Field(default=0.0, ge=0)


class ActualizarProductoRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    categoria: str | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    precio_unitario: float | None = Field(default=None, ge=0)


class ProductoResponse(BaseModel):
    id: str
    codigo: str
    nombre: str
    descripcion: str | None
    categoria: str | None
    stock_minimo: int
    stock_actual: int
    precio_unitario: float
    imagen_url: str | None


class ProductosPaginadosResponse(BaseModel):
    resultado: list[ProductoResponse]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int


class MessageResponse(BaseModel):
    message: str
