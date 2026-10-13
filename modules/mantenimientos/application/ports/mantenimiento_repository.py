from abc import ABC, abstractmethod
from datetime import datetime

from modules.mantenimientos.domain.entities import EstadoMantenimiento, Mantenimiento, TipoMantenimiento


class MantenimientoRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, mantenimiento: Mantenimiento) -> Mantenimiento: ...

    @abstractmethod
    async def guardar_varios(self, mantenimientos: list[Mantenimiento]) -> list[Mantenimiento]: ...

    @abstractmethod
    async def obtener_por_id(self, id_mantenimiento: str) -> Mantenimiento | None: ...

    @abstractmethod
    async def listar(
        self,
        activo_id: str | None,
        tecnico_responsable_id: str | None,
        estado: EstadoMantenimiento | None,
        tipo: TipoMantenimiento | None,
        solicitud_id: str | None,
        skip: int,
        limit: int,
    ) -> list[Mantenimiento]: ...

    @abstractmethod
    async def contar(
        self,
        activo_id: str | None,
        tecnico_responsable_id: str | None,
        estado: EstadoMantenimiento | None,
        tipo: TipoMantenimiento | None,
        solicitud_id: str | None,
    ) -> int: ...

    @abstractmethod
    async def listar_pendientes_de_alerta(self, limite_fecha: datetime) -> list[Mantenimiento]: ...
