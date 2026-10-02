from pydantic import BaseModel, Field


class CrearTareaInput(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
