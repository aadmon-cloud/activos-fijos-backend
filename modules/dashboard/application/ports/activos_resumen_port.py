from abc import ABC, abstractmethod

from modules.dashboard.domain.entities import ResumenActivos


class ActivosResumenPort(ABC):
    @abstractmethod
    async def obtener(self) -> ResumenActivos: ...
