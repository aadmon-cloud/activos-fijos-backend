from pydantic import BaseModel, Field


class ItemSalidaPorMercadoInput(BaseModel):
    """Ubicación de origen para UN producto del mercado. Cada producto del kit
    puede vivir en una ubicación física distinta — no hay una única ubicación
    global válida para todo el mercado (ver `MovimientoUbicacionNoEspecificadaError`).
    """

    producto_codigo: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1)


class RegistrarSalidaPorMercadoInput(BaseModel):
    mercado_nombre: str = Field(min_length=1)
    productos: list[ItemSalidaPorMercadoInput] = Field(min_length=1)
    cantidad: int = Field(default=1, ge=1)
    cliente_destino: str | None = None
    notas: str | None = None
    referencia: str | None = None
