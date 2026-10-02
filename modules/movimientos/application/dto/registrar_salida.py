from pydantic import BaseModel, Field


class RegistrarSalidaInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str = Field(min_length=1)
    motivo: str | None = None
    cliente_destino: str | None = None
    notas: str | None = None
