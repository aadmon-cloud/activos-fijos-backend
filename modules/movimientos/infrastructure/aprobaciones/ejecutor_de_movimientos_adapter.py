from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.application.ports.ejecutor_de_movimientos import (
    EjecutorDeMovimientosPort,
)
from modules.movimientos.application.services.registrar_entrada import RegistrarEntradaService
from modules.movimientos.application.services.registrar_entrada_multiple import (
    RegistrarEntradaMultipleService,
)
from modules.movimientos.application.services.registrar_salida import RegistrarSalidaService
from modules.movimientos.application.services.registrar_salida_multiple import (
    RegistrarSalidaMultipleService,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class MovimientosEjecutorAdapter(EjecutorDeMovimientosPort):
    """Envoltorio delgado sobre los 4 servicios ya existentes de `movimientos`,
    consumido por `aprobaciones_pendientes` al confirmar una propuesta."""

    def __init__(
        self,
        registrar_entrada: RegistrarEntradaService,
        registrar_entrada_multiple: RegistrarEntradaMultipleService,
        registrar_salida: RegistrarSalidaService,
        registrar_salida_multiple: RegistrarSalidaMultipleService,
    ):
        self._registrar_entrada = registrar_entrada
        self._registrar_entrada_multiple = registrar_entrada_multiple
        self._registrar_salida = registrar_salida
        self._registrar_salida_multiple = registrar_salida_multiple

    async def registrar_entrada(
        self, entrada: RegistrarEntradaInput, creado_por: AuditPersona, uow: UnitOfWorkPort
    ) -> Movimiento:
        return await self._registrar_entrada.ejecutar(entrada, creado_por, uow=uow)

    async def registrar_entrada_multiple(
        self,
        entrada: RegistrarEntradaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Movimiento:
        return await self._registrar_entrada_multiple.ejecutar(entrada, creado_por, uow=uow)

    async def registrar_salida(
        self, entrada: RegistrarSalidaInput, creado_por: AuditPersona, uow: UnitOfWorkPort
    ) -> Movimiento:
        return await self._registrar_salida.ejecutar(entrada, creado_por, uow=uow)

    async def registrar_salida_multiple(
        self,
        entrada: RegistrarSalidaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Movimiento:
        return await self._registrar_salida_multiple.ejecutar(entrada, creado_por, uow=uow)
