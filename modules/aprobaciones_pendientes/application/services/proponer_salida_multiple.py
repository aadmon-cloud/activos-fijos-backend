from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.movimientos.application.dto.registrar_salida_multiple import (
    RegistrarSalidaMultipleInput,
)
from shared.domain.entities.audit_persona import AuditPersona


class ProponerSalidaMultipleService:
    def __init__(self, movimiento_pendiente_repository: MovimientoPendienteRepositoryPort):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository

    async def ejecutar(
        self, entrada: RegistrarSalidaMultipleInput, creado_por: AuditPersona
    ) -> MovimientoPendiente:
        pendiente = MovimientoPendiente.proponer(
            tipo_propuesto="salida_multiple",
            payload=entrada.model_dump(),
            creado_por=creado_por,
        )
        return await self._movimiento_pendiente_repository.crear(pendiente)
