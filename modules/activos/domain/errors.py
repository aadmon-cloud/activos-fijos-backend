from shared.domain.errors import DomainError, ErrorCategory


class ActivoNumeroInventarioDuplicadoError(DomainError):
    def __init__(self, numero_inventario: str):
        super().__init__(
            f"Ya existe un activo con el numero de inventario '{numero_inventario}'.",
            code="ACT-001",
            category=ErrorCategory.CONFLICT,
        )


class ActivoNoEncontradoError(DomainError):
    def __init__(self, id_activo: str):
        super().__init__(
            f"El activo '{id_activo}' no existe.",
            code="ACT-002",
            category=ErrorCategory.NOT_FOUND,
        )


class TransicionEstadoInvalidaError(DomainError):
    def __init__(self, desde: str, hacia: str):
        super().__init__(
            f"No se puede cambiar el estado de '{desde}' a '{hacia}'.",
            code="ACT-003",
            category=ErrorCategory.BUSINESS_RULE,
        )


class ComplementoCantidadInvalidaError(DomainError):
    def __init__(self, nombre_complemento: str):
        super().__init__(
            f"La cantidad del complemento '{nombre_complemento}' debe ser al menos 1.",
            code="ACT-005",
            category=ErrorCategory.VALIDATION,
        )


class FotoTipoNoPermitidoError(DomainError):
    def __init__(self):
        super().__init__(
            "La foto debe ser una imagen JPEG, PNG o WebP.",
            code="ACT-006",
            category=ErrorCategory.VALIDATION,
        )


class FotoDemasiadoGrandeError(DomainError):
    def __init__(self):
        super().__init__(
            "La foto supera el tamano maximo permitido (5 MB).",
            code="ACT-007",
            category=ErrorCategory.VALIDATION,
        )


class FotoNoEncontradaError(DomainError):
    def __init__(self, id_activo: str):
        super().__init__(
            f"El activo '{id_activo}' no tiene foto.",
            code="ACT-008",
            category=ErrorCategory.NOT_FOUND,
        )
