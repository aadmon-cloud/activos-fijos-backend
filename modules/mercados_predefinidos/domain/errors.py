from shared.domain.errors import DomainError, ErrorCategory


class MercadoNombreDuplicadoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            message=f"Ya existe un mercado predefinido con el nombre '{nombre}'.",
            code="MERC-001",
            category=ErrorCategory.CONFLICT,
            details={"nombre": nombre},
        )


class MercadoNoEncontradoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            message=f"No existe un mercado predefinido con el nombre '{nombre}'.",
            code="MERC-002",
            category=ErrorCategory.NOT_FOUND,
            details={"nombre": nombre},
        )


class MercadoProductosVacioError(DomainError):
    def __init__(self):
        super().__init__(
            message="El mercado predefinido debe tener al menos un producto.",
            code="MERC-003",
            category=ErrorCategory.VALIDATION,
        )
