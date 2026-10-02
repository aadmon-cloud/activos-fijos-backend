from pydantic import BaseModel, Field


class ItemSalidaMultipleInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)


class RegistrarSalidaMultipleInput(BaseModel):
    productos: list[ItemSalidaMultipleInput] = Field(min_length=1)
    motivo: str = Field(min_length=1)
    cliente_destino: str | None = None
    notas: str | None = None
