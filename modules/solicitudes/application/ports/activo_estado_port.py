from abc import ABC, abstractmethod


class ActivoEstadoPort(ABC):
    """Consulta y cambia el estado del ciclo de vida del activo al que se refiere una solicitud."""

    @abstractmethod
    async def obtener_estado(self, activo_id: str) -> str | None:
        """Estado actual del activo; None si no existe."""

    @abstractmethod
    async def cambiar_estado(
        self, activo_id: str, estado_nuevo: str, actor_id: str, actor_nombre: str
    ) -> bool:
        """Cambia el estado dejando constancia en el historial del activo.

        Devuelve False si el activo no existe o la transicion no esta permitida.
        """
