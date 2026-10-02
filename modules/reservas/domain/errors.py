from shared.domain.errors import DomainError, ErrorCategory


class ReservaSinItemsError(DomainError):
    def __init__(self):
        super().__init__(
            message="La reserva debe tener al menos un item.",
            code="RES-001",
            category=ErrorCategory.VALIDATION,
        )


class ReservaNoEncontradaError(DomainError):
    def __init__(self, session_id: str):
        super().__init__(
            message=f"No existe una reserva para la sesión '{session_id}'.",
            code="RES-002",
            category=ErrorCategory.NOT_FOUND,
            details={"session_id": session_id},
        )


class StockDisponibleInsuficienteError(DomainError):
    def __init__(self, producto_codigo: str, ubicacion: str, disponible: int, solicitado: int):
        super().__init__(
            message=(
                f"Stock disponible insuficiente para '{producto_codigo}' en '{ubicacion}': "
                f"disponible {disponible}, solicitado {solicitado}."
            ),
            code="RES-003",
            category=ErrorCategory.VALIDATION,
            details={
                "producto_codigo": producto_codigo,
                "ubicacion": ubicacion,
                "disponible": disponible,
                "solicitado": solicitado,
            },
        )
