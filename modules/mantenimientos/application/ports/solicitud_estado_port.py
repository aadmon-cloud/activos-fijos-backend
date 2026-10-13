from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ActorSolicitud:
    id: str
    nombre: str
    rol: str
    area_id: str | None


class SolicitudEstadoPort(ABC):
    @abstractmethod
    async def marcar_resuelta(self, solicitud_id: str, actor: ActorSolicitud) -> None: ...
