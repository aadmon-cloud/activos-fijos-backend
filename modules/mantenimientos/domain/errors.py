from shared.domain.errors import DomainError, ErrorCategory


class MantenimientoNoEncontradoError(DomainError):
    def __init__(self, id_mantenimiento: str):
        super().__init__(
            f"El mantenimiento '{id_mantenimiento}' no existe.",
            code="MNT-001",
            category=ErrorCategory.NOT_FOUND,
        )


class ActivoNoEncontradoParaMantenimientoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no existe.",
            code="MNT-002",
            category=ErrorCategory.NOT_FOUND,
        )


class TecnicoInvalidoError(DomainError):
    def __init__(self, usuario_id: str):
        super().__init__(
            f"El usuario '{usuario_id}' no tiene el rol de mantenimiento.",
            code="MNT-003",
            category=ErrorCategory.BUSINESS_RULE,
        )


class TransicionEstadoMantenimientoInvalidaError(DomainError):
    def __init__(self, desde: str, hacia: str):
        super().__init__(
            f"No se puede cambiar el mantenimiento de '{desde}' a '{hacia}'.",
            code="MNT-004",
            category=ErrorCategory.BUSINESS_RULE,
        )


class ArchivoTipoNoPermitidoError(DomainError):
    def __init__(self):
        super().__init__(
            "El archivo debe ser JPEG, PNG, WebP o PDF.",
            code="MNT-005",
            category=ErrorCategory.VALIDATION,
        )


class ArchivoDemasiadoGrandeError(DomainError):
    def __init__(self):
        super().__init__(
            "El archivo supera el tamano maximo permitido.",
            code="MNT-006",
            category=ErrorCategory.VALIDATION,
        )


class ArchivoNoEncontradoError(DomainError):
    def __init__(self, archivo_id: str):
        super().__init__(
            f"El archivo '{archivo_id}' no existe en este mantenimiento.",
            code="MNT-007",
            category=ErrorCategory.NOT_FOUND,
        )


class SolicitudNoValidaParaMantenimientoError(DomainError):
    def __init__(self, solicitud_id: str):
        super().__init__(
            f"La solicitud '{solicitud_id}' no existe o no corresponde al activo del mantenimiento.",
            code="MNT-008",
            category=ErrorCategory.BUSINESS_RULE,
        )


class CodigosMasivosVaciosError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar al menos un codigo de activo.",
            code="MNT-009",
            category=ErrorCategory.VALIDATION,
        )


class DemasiadosCodigosMasivosError(DomainError):
    def __init__(self, limite: int):
        super().__init__(
            f"No se pueden registrar mas de {limite} codigos en una sola carga.",
            code="MNT-010",
            category=ErrorCategory.VALIDATION,
            details={"limite": limite},
        )
