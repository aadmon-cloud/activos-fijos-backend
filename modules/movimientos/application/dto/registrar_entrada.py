from pydantic import BaseModel, Field


class RegistrarEntradaInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    tipo_origen: str | None = None
    origen_nombre: str | None = None
    ubicacion: str | None = None
    notas: str | None = None
