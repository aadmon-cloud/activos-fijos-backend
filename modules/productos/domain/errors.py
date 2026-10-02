from shared.domain.errors import DomainError, ErrorCategory


class ProductoCodigoDuplicadoError(DomainError):
    def __init__(self, codigo: str):
        super().__init__(
            message=f"El código '{codigo}' ya está registrado.",
            code="PROD-001",
            category=ErrorCategory.CONFLICT,
            details={"codigo": codigo},
        )


class ProductoNoEncontradoError(DomainError):
    def __init__(self, codigo: str):
        super().__init__(
            message=f"No existe un producto con código '{codigo}'.",
            code="PROD-002",
            category=ErrorCategory.NOT_FOUND,
            details={"codigo": codigo},
        )
