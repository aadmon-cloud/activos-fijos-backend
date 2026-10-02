from pydantic import BaseModel, Field


class AjusteItemInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1)
    diferencia: int
