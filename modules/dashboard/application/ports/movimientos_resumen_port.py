from abc import ABC, abstractmethod

from modules.dashboard.domain.entities import ResumenMovimientos


class MovimientosResumenPort(ABC):
    @abstractmethod
    async def obtener(self) -> ResumenMovimientos: ...
