from abc import ABC, abstractmethod

from modules.notificaciones.domain.entities import EstadoNotificacion, Notificacion


class NotificacionRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, notificacion: Notificacion) -> Notificacion: ...

    @abstractmethod
    async def obtener_por_id(self, id_notificacion: str) -> Notificacion | None: ...

    @abstractmethod
    async def listar(
        self, estado: EstadoNotificacion | None, skip: int, limit: int
    ) -> list[Notificacion]: ...

    @abstractmethod
    async def contar(self, estado: EstadoNotificacion | None) -> int: ...
