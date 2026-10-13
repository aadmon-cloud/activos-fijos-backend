from abc import ABC, abstractmethod


class TareaRecordatorioPort(ABC):
    @abstractmethod
    async def ejecutar(self) -> int:
        """Envia los recordatorios pendientes y devuelve cuantos envio."""
