from shared.domain.errors import DomainError, ErrorCategory


class MovimientoPendienteNoEncontradoError(DomainError):
    def __init__(self, movimiento_pendiente_id: str):
        super().__init__(
            message=f"No existe una propuesta pendiente con id '{movimiento_pendiente_id}'.",
            code="APR-001",
            category=ErrorCategory.NOT_FOUND,
            details={"movimiento_pendiente_id": movimiento_pendiente_id},
        )


class MovimientoPendienteYaConfirmadoError(DomainError):
    def __init__(self, movimiento_pendiente_id: str):
        super().__init__(
            message=(
                f"La propuesta '{movimiento_pendiente_id}' ya fue confirmada — no puede "
                "confirmarse ni eliminarse de nuevo."
            ),
            code="APR-002",
            category=ErrorCategory.CONFLICT,
            details={"movimiento_pendiente_id": movimiento_pendiente_id},
        )


class PendienteNoPerteneceAlUsuarioError(DomainError):
    def __init__(self, movimiento_pendiente_id: str):
        super().__init__(
            message=(
                f"La propuesta '{movimiento_pendiente_id}' no te pertenece — solo el "
                "usuario que la propuso o un super_admin pueden eliminarla."
            ),
            code="APR-003",
            category=ErrorCategory.FORBIDDEN,
            details={"movimiento_pendiente_id": movimiento_pendiente_id},
        )
