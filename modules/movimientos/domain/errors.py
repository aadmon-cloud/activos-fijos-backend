from shared.domain.errors import DomainError, ErrorCategory


class MovimientoUbicacionRequeridaError(DomainError):
    def __init__(self):
        super().__init__(
            message="Para registrar una salida, la ubicación es obligatoria.",
            code="MOV-001",
            category=ErrorCategory.VALIDATION,
        )


class MovimientoUbicacionNoEncontradaError(DomainError):
    def __init__(self, producto_codigo: str, ubicacion: str):
        super().__init__(
            message=(
                f"El producto '{producto_codigo}' no tiene una ubicación "
                f"llamada '{ubicacion}'."
            ),
            code="MOV-002",
            category=ErrorCategory.NOT_FOUND,
            details={"producto_codigo": producto_codigo, "ubicacion": ubicacion},
        )


class ModalidadReservaNoSoportadaError(DomainError):
    def __init__(self, session_id: str, modalidad: str):
        super().__init__(
            message=(
                f"La reserva de la sesión '{session_id}' es modalidad '{modalidad}', "
                "todavía no soportada por este endpoint."
            ),
            code="MOV-004",
            category=ErrorCategory.VALIDATION,
            details={"session_id": session_id, "modalidad": modalidad},
        )


class MovimientoStockInsuficienteError(DomainError):
    def __init__(self, producto_codigo: str, ubicacion: str, disponible: int, solicitado: int):
        super().__init__(
            message=(
                f"Stock insuficiente en '{ubicacion}' para el producto "
                f"'{producto_codigo}'. Disponible: {disponible}, solicitado: {solicitado}."
            ),
            code="MOV-003",
            category=ErrorCategory.BUSINESS_RULE,
            details={
                "producto_codigo": producto_codigo,
                "ubicacion": ubicacion,
                "disponible": disponible,
                "solicitado": solicitado,
            },
        )


class MovimientoNoEncontradoError(DomainError):
    def __init__(self, movimiento_id: str):
        super().__init__(
            message=f"No existe una salida con id '{movimiento_id}'.",
            code="MOV-005",
            category=ErrorCategory.NOT_FOUND,
            details={"movimiento_id": movimiento_id},
        )


class ArchivoNoEsPdfError(DomainError):
    def __init__(self, nombre_archivo: str):
        super().__init__(
            message=f"El archivo '{nombre_archivo}' no es un PDF.",
            code="MOV-006",
            category=ErrorCategory.VALIDATION,
            details={"nombre_archivo": nombre_archivo},
        )


class PdfFirmadoNoEncontradoError(DomainError):
    def __init__(self, movimiento_id: str):
        super().__init__(
            message=f"La salida '{movimiento_id}' todavía no tiene un PDF firmado subido.",
            code="MOV-007",
            category=ErrorCategory.NOT_FOUND,
            details={"movimiento_id": movimiento_id},
        )


class MovimientoUbicacionNoEspecificadaError(DomainError):
    """Salida por mercado: cada producto del kit puede vivir en una ubicación
    física distinta, así que la request debe indicar la ubicación de cada uno
    explícitamente — no existe una única ubicación global válida para todos."""

    def __init__(self, producto_codigo: str):
        super().__init__(
            message=(
                f"Debes indicar la ubicación de origen del producto '{producto_codigo}' "
                "para registrar la salida de este mercado."
            ),
            code="MOV-009",
            category=ErrorCategory.VALIDATION,
            details={"producto_codigo": producto_codigo},
        )


class MovimientoSinProductosError(DomainError):
    """Reutilizado por toda modalidad multi-producto (entrada múltiple, salida
    múltiple, kit, mercado) — no es específico de la entrada múltiple."""

    def __init__(self):
        super().__init__(
            message="Debe haber al menos un producto para registrar este movimiento.",
            code="MOV-008",
            category=ErrorCategory.VALIDATION,
        )
