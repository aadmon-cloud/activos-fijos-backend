from abc import ABC, abstractmethod

from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class EjecutorDeMovimientosPort(ABC):
    """Puerto consumido por `aprobaciones_pendientes` para aplicar, al confirmar
    una propuesta, el movimiento real correspondiente — propiedad de
    `movimientos`, que es quien tiene los servicios concretos. Cada método
    acepta `uow` para participar de la transacción externa del llamador."""

    @abstractmethod
    async def registrar_entrada(
        self, entrada: RegistrarEntradaInput, creado_por: AuditPersona, uow: UnitOfWorkPort
    ) -> Movimiento: ...

    @abstractmethod
    async def registrar_entrada_multiple(
        self,
        entrada: RegistrarEntradaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Movimiento: ...

    @abstractmethod
    async def registrar_salida(
        self, entrada: RegistrarSalidaInput, creado_por: AuditPersona, uow: UnitOfWorkPort
    ) -> Movimiento: ...

    @abstractmethod
    async def registrar_salida_multiple(
        self,
        entrada: RegistrarSalidaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Movimiento: ...
