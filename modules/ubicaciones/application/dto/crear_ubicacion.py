from pydantic import BaseModel, Field


class CrearUbicacionInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(default=0, ge=0)
