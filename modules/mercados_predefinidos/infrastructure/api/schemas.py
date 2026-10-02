from pydantic import BaseModel, Field


class ProductoKitRequest(BaseModel):
    producto_id: str = Field(min_length=1)
    cantidad: int = Field(gt=0)


class CrearMercadoPredefinidoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None
    productos: list[ProductoKitRequest] = Field(min_length=1)


class ActualizarMercadoPredefinidoRequest(BaseModel):
    descripcion: str | None = None
    productos: list[ProductoKitRequest] | None = Field(default=None, min_length=1)
    activo: bool | None = None


class ProductoKitResponse(BaseModel):
    producto_id: str
    cantidad: int
    producto_nombre: str


class MercadoPredefinidoResponse(BaseModel):
    id: str
    nombre: str
    descripcion: str | None
    productos: list[ProductoKitResponse]
    activo: bool


class MessageResponse(BaseModel):
    message: str
