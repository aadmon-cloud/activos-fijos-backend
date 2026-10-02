from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from shared.domain.entities.base import BaseDomainEntity

from modules.ejemplo_tareas.domain.errors import (
    TareaYaCompletadaError,
    TituloTareaInvalidoError,
)


class Tarea(BaseDomainEntity):
    id: str
    titulo: str
    descripcion: str | None = None
    completada: bool = False
    creada_en: datetime
    completada_en: datetime | None = None

    @classmethod
    def crear(cls, titulo: str, descripcion: str | None = None) -> "Tarea":
        titulo_limpio = titulo.strip()
        descripcion_limpia = descripcion.strip() if descripcion else None

        if not titulo_limpio:
            raise TituloTareaInvalidoError()

        return cls(
            id=str(uuid4()),
            titulo=titulo_limpio,
            descripcion=descripcion_limpia or None,
            completada=False,
            creada_en=datetime.now(UTC),
            completada_en=None,
        )

    def completar(self) -> "Tarea":
        if self.completada:
            raise TareaYaCompletadaError(self.id)

        return self.model_copy(
            update={
                "completada": True,
                "completada_en": datetime.now(UTC),
            }
        )
