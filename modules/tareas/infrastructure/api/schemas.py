from datetime import datetime

from pydantic import BaseModel, Field


class CrearTareaRequest(BaseModel):
    titulo: str = Field(min_length=1)


class TareaResponse(BaseModel):
    id: str
    titulo: str
    completada: bool
    fecha_creacion: datetime
