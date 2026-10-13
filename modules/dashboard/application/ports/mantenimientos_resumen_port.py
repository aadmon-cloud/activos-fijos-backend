from abc import ABC, abstractmethod

from modules.dashboard.domain.entities import ResumenMantenimientos


class MantenimientosResumenPort(ABC):
    @abstractmethod
    async def obtener(self) -> ResumenMantenimientos: ...
