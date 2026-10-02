from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.errors import MovimientoPendienteNoEncontradoError
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
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.domain.entities.audit_persona import AuditPersona

# tipo_propuesto -> (DTO de `movimientos` a reconstruir desde `payload`, método de
# `EjecutorDeMovimientosPort` a invocar). Agregar un `TipoPropuesto` nuevo es agregar una
# entrada acá, no tocar `ejecutar()`.
_ESTRATEGIAS_POR_TIPO: dict[str, tuple[type, str]] = {
    "entrada": (RegistrarEntradaInput, "registrar_entrada"),
    "entrada_multiple": (RegistrarEntradaMultipleInput, "registrar_entrada_multiple"),
    "salida": (RegistrarSalidaInput, "registrar_salida"),
    "salida_multiple": (RegistrarSalidaMultipleInput, "registrar_salida_multiple"),
}


class ConfirmarMovimientoPendienteService:
    """Dispatcher: obtiene la propuesta, reconstruye el `Input` real de
    `movimientos` desde su `payload` según `tipo_propuesto`, y aplica el
    movimiento real y la actualización de la propuesta dentro de una única
    transacción (evita el riesgo de duplicado si el segundo paso fallara
    después de que el primero ya tuvo éxito)."""

    def __init__(
        self,
        movimiento_pendiente_repository: MovimientoPendienteRepositoryPort,
        ejecutor_de_movimientos: EjecutorDeMovimientosPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository
        self._ejecutor_de_movimientos = ejecutor_de_movimientos
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self, movimiento_pendiente_id: str, confirmado_por: AuditPersona
    ) -> Movimiento:
        """Raises:
        MovimientoPendienteNoEncontradoError: no existe una propuesta con ese id.
        MovimientoPendienteYaConfirmadoError: la propuesta ya fue confirmada.
        Los errores propios del movimiento real (producto/ubicación/stock) según el tipo.
        """
        pendiente = await self._movimiento_pendiente_repository.obtener_por_id(
            movimiento_pendiente_id
        )
        if pendiente is None:
            raise MovimientoPendienteNoEncontradoError(movimiento_pendiente_id)

        async with self._unit_of_work_factory() as uow:
            movimiento = await self._aplicar_movimiento_real(pendiente, confirmado_por, uow)

            pendiente_confirmada = pendiente.confirmar(
                movimiento_id=movimiento.id, confirmado_por=confirmado_por
            )
            await self._movimiento_pendiente_repository.actualizar(pendiente_confirmada, uow=uow)

        return movimiento

    async def _aplicar_movimiento_real(self, pendiente, confirmado_por, uow) -> Movimiento:
        dto_class, metodo_ejecutor = _ESTRATEGIAS_POR_TIPO[pendiente.tipo_propuesto]
        entrada = dto_class(**pendiente.payload)
        ejecutar_movimiento = getattr(self._ejecutor_de_movimientos, metodo_ejecutor)
        return await ejecutar_movimiento(entrada, confirmado_por, uow)
