from abc import ABC, abstractmethod

from modules.activos.domain.entities import EntradaHistorialActivo


class HistorialActivoRepositoryPort(ABC):
    @abstractmethod
    async def registrar(self, entrada: EntradaHistorialActivo) -> EntradaHistorialActivo: ...

    @abstractmethod
    async def listar_por_activo(self, activo_id: str) -> list[EntradaHistorialActivo]: ...
