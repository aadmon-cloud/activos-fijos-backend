from abc import ABC, abstractmethod

from shared.application.persistence.unit_of_work import UnitOfWorkPort


class GeneradorSecuencialPort(ABC):
    @abstractmethod
    async def siguiente(
        self,
        nombre: str,
        prefijo: str,
        ancho: int = 3,
        uow: UnitOfWorkPort | None = None,
    ) -> str:
        """Atomically increment and return the next formatted value (e.g. "RM-001").

        `nombre` identifica la secuencia (ej. "remision"). `prefijo` se usa solo
        para inicializar el contador si todavía no existe — en llamadas
        posteriores se ignora y se respeta el `prefijo` ya guardado. Cuando se
        provee `uow`, el incremento participa de esa transacción (evita huecos
        de numeración si el resto de la operación hace rollback).
        """
