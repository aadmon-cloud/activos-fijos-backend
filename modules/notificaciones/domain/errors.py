from shared.domain.errors import DomainError, ErrorCategory


class NotificacionNoEncontradaError(DomainError):
    def __init__(self, id_notificacion: str):
        super().__init__(
            f"La notificacion '{id_notificacion}' no existe.",
            code="NTF-001",
            category=ErrorCategory.NOT_FOUND,
        )


class NotificacionNoReenviableError(DomainError):
    def __init__(self, id_notificacion: str):
        super().__init__(
            f"La notificacion '{id_notificacion}' ya se envio: no se puede reenviar.",
            code="NTF-002",
            category=ErrorCategory.BUSINESS_RULE,
        )
