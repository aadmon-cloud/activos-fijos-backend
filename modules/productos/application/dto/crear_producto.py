from pydantic import BaseModel, Field


class CrearProductoInput(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    categoria: str | None = None
    stock_minimo: int = Field(default=0, ge=0)
    precio_unitario: float = Field(default=0.0, ge=0)
