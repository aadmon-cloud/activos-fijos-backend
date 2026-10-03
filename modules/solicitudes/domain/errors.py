from shared.domain.errors import DomainError, ErrorCategory


class SolicitudNoEncontradaError(DomainError):
    def __init__(self, id_solicitud: str):
        super().__init__(
            f"La solicitud '{id_solicitud}' no existe.",
            code="SOL-001",
            category=ErrorCategory.NOT_FOUND,
        )


class ActivoNoEncontradoParaSolicitudError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no existe.",
            code="SOL-002",
            category=ErrorCategory.NOT_FOUND,
        )


class ActivoNoAsignadoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"Solo el responsable del activo '{activo_id}' puede crear una solicitud sobre el.",
            code="SOL-003",
            category=ErrorCategory.BUSINESS_RULE,
        )


class TransicionEstadoSolicitudInvalidaError(DomainError):
    def __init__(self, desde: str, hacia: str):
        super().__init__(
            f"No se puede cambiar la solicitud de '{desde}' a '{hacia}'.",
            code="SOL-004",
            category=ErrorCategory.BUSINESS_RULE,
        )


class SolicitudSinPermisoError(DomainError):
    def __init__(self, id_solicitud: str):
        super().__init__(
            f"No tiene permisos para gestionar la solicitud '{id_solicitud}'.",
            code="SOL-005",
            category=ErrorCategory.FORBIDDEN,
        )


class DescripcionVaciaError(DomainError):
    def __init__(self):
        super().__init__(
            "La descripcion de la solicitud no puede estar vacia.",
            code="SOL-006",
            category=ErrorCategory.VALIDATION,
        )
