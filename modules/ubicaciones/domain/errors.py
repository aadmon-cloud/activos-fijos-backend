from shared.domain.errors import DomainError, ErrorCategory


class UbicacionDuplicadaError(DomainError):
    def __init__(self, producto_codigo: str, ubicacion: str):
        super().__init__(
            message=f"La ubicación '{ubicacion}' ya existe para el producto '{producto_codigo}'.",
            code="UBIC-001",
            category=ErrorCategory.CONFLICT,
            details={"producto_codigo": producto_codigo, "ubicacion": ubicacion},
        )


class UbicacionNoEncontradaError(DomainError):
    def __init__(self, producto_codigo: str, ubicacion: str):
        super().__init__(
            message=f"No existe la ubicación '{ubicacion}' para el producto '{producto_codigo}'.",
            code="UBIC-002",
            category=ErrorCategory.NOT_FOUND,
            details={"producto_codigo": producto_codigo, "ubicacion": ubicacion},
        )


class StockInsuficienteError(DomainError):
    def __init__(self, ubicacion: str, disponible: int, solicitado: int):
        super().__init__(
            message=(
                f"Stock insuficiente en '{ubicacion}': disponible {disponible}, "
                f"solicitado {solicitado}."
            ),
            code="UBIC-003",
            category=ErrorCategory.VALIDATION,
            details={"ubicacion": ubicacion, "disponible": disponible, "solicitado": solicitado},
        )
