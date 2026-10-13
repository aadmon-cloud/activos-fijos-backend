from abc import ABC, abstractmethod

from modules.dashboard.domain.entities import ResumenAuditorias


class AuditoriasResumenPort(ABC):
    @abstractmethod
    async def obtener(self, limite_recientes: int) -> ResumenAuditorias: ...
