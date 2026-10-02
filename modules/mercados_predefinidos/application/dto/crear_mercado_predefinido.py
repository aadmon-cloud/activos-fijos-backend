from pydantic import BaseModel, Field

from modules.mercados_predefinidos.application.dto.producto_kit import ProductoKitInput


class CrearMercadoPredefinidoInput(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None
    productos: list[ProductoKitInput] = Field(min_length=1)
