from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from shared.domain.entities.audit_persona import AuditPersona


class ProponerEntradaService:
    def __init__(self, movimiento_pendiente_repository: MovimientoPendienteRepositoryPort):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository

    async def ejecutar(
        self, entrada: RegistrarEntradaInput, creado_por: AuditPersona
    ) -> MovimientoPendiente:
        pendiente = MovimientoPendiente.proponer(
            tipo_propuesto="entrada",
            payload=entrada.model_dump(),
            creado_por=creado_por,
        )
        return await self._movimiento_pendiente_repository.crear(pendiente)
