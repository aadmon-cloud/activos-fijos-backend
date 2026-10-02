from pydantic import BaseModel, Field

from modules.productos.infrastructure.api.schemas import ProductoResponse


class CrearUbicacionRequest(BaseModel):
    ubicacion: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(default=0, ge=0)


class ActualizarUbicacionRequest(BaseModel):
    cantidad: int = Field(ge=0)


class TransferirStockRequest(BaseModel):
    origen: str = Field(min_length=1, max_length=100)
    destino: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(ge=1)


class UbicacionResponse(BaseModel):
    id: str
    producto_codigo: str
    ubicacion: str
    stock_fisico: int
    stock_reservado: int
    stock_disponible: int


class ProductoConUbicacionesResponse(BaseModel):
    producto: ProductoResponse
    ubicaciones: list[UbicacionResponse]
    total_ubicaciones: int


class MessageResponse(BaseModel):
    message: str
