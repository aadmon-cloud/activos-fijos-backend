from abc import ABC, abstractmethod


class SolicitudVerificadorPort(ABC):
    @abstractmethod
    async def corresponde_al_activo(self, solicitud_id: str, activo_id: str) -> bool:
        """Si la solicitud existe y se refiere a ese activo."""
