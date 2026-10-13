from abc import ABC, abstractmethod

from modules.dashboard.domain.entities import ResumenSolicitudes


class SolicitudesResumenPort(ABC):
    @abstractmethod
    async def obtener(self) -> ResumenSolicitudes: ...
