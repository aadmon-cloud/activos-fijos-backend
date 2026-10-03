from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ActivoResumen:
    id: str
    responsable_id: str
    area_id: str


class ActivoResumenPort(ABC):
    @abstractmethod
    async def obtener_resumen(self, activo_id: str) -> ActivoResumen | None: ...
