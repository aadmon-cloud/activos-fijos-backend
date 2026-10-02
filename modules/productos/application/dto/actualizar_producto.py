from pydantic import BaseModel, Field


class ActualizarProductoInput(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    categoria: str | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    precio_unitario: float | None = Field(default=None, ge=0)
