from pydantic import BaseModel, Field

from modules.mercados_predefinidos.application.dto.producto_kit import ProductoKitInput


class ActualizarMercadoPredefinidoInput(BaseModel):
    descripcion: str | None = None
    productos: list[ProductoKitInput] | None = Field(default=None, min_length=1)
    activo: bool | None = None
