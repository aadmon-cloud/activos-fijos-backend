from datetime import datetime

from pydantic import BaseModel, Field


class AjusteItemRequest(BaseModel):
    producto_codigo: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1)
    diferencia: int


class AjustarReservaRequest(BaseModel):
    ajustes: list[AjusteItemRequest] = Field(min_length=1)
    datos_adicionales: dict | None = None


class ItemReservaResponse(BaseModel):
    producto_codigo: str
    ubicacion: str
    cantidad: int


class ReservaResponse(BaseModel):
    id: str
    session_id: str
    items: list[ItemReservaResponse]
    datos_adicionales: dict | None
    ultima_actividad: datetime


class StockDisponibleResponse(BaseModel):
    producto_codigo: str
    ubicacion: str
    stock_fisico: int
    reservado_otros: int
    reservado_actual: int
    disponible: int


class MessageResponse(BaseModel):
    message: str
