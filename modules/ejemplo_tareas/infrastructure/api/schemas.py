from datetime import datetime

from pydantic import BaseModel, Field


class CrearTareaRequest(BaseModel):
    titulo: str = Field(min_length=1, max_length=120, examples=["Preparar onboarding"])
    descripcion: str | None = Field(
        default=None,
        max_length=500,
        examples=["Documentar el flujo para nuevos desarrolladores."],
    )


class TareaResponse(BaseModel):
    id: str
    titulo: str
    descripcion: str | None = None
    completada: bool
    creada_en: datetime
    completada_en: datetime | None = None


class TareasPaginadasResponse(BaseModel):
    resultado: list[TareaResponse]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int
