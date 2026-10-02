from pydantic import BaseModel, Field


class ActualizarUbicacionInput(BaseModel):
    cantidad: int = Field(ge=0)
