from shared.domain.errors import DomainError, ErrorCategory


class ActivoNoEncontradoParaMovimientoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no existe.",
            code="MOV-001",
            category=ErrorCategory.NOT_FOUND,
        )


class UsuarioDestinoNoEncontradoError(DomainError):
    def __init__(self, usuario_id: str):
        super().__init__(
            f"El usuario destino '{usuario_id}' no existe.",
            code="MOV-002",
            category=ErrorCategory.NOT_FOUND,
        )


class ActivoNoDisponibleError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no esta disponible.",
            code="MOV-003",
            category=ErrorCategory.BUSINESS_RULE,
        )


class MovimientoActivoYaExisteError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' ya tiene un movimiento en curso.",
            code="MOV-004",
            category=ErrorCategory.CONFLICT,
        )


class MovimientoNoEncontradoError(DomainError):
    def __init__(self, id_movimiento: str):
        super().__init__(
            f"El movimiento '{id_movimiento}' no existe.",
            code="MOV-005",
            category=ErrorCategory.NOT_FOUND,
        )


class TransicionEstadoMovimientoInvalidaError(DomainError):
    def __init__(self, desde: str, hacia: str):
        super().__init__(
            f"No se puede cambiar el movimiento de '{desde}' a '{hacia}'.",
            code="MOV-006",
            category=ErrorCategory.BUSINESS_RULE,
        )


class PermisoAprobacionError(DomainError):
    def __init__(self, id_movimiento: str):
        super().__init__(
            f"No tiene permiso para decidir sobre el movimiento '{id_movimiento}' en este paso.",
            code="MOV-007",
            category=ErrorCategory.FORBIDDEN,
        )


class ComprobanteNoDisponibleError(DomainError):
    def __init__(self, id_movimiento: str):
        super().__init__(
            f"El movimiento '{id_movimiento}' aun no tiene un comprobante generado.",
            code="MOV-008",
            category=ErrorCategory.NOT_FOUND,
        )


class MotivoRechazoObligatorioError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar el motivo del rechazo.",
            code="MOV-009",
            category=ErrorCategory.VALIDATION,
        )


class SolicitudDeBajaRequiereAdminError(DomainError):
    def __init__(self):
        super().__init__(
            "Solo un administrador general puede solicitar la baja de un activo.",
            code="MOV-010",
            category=ErrorCategory.FORBIDDEN,
        )


class OperacionSobreActivoFallidaError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"No se pudo aplicar el cambio sobre el activo '{activo_id}'.",
            code="MOV-011",
            category=ErrorCategory.BUSINESS_RULE,
        )


class DescripcionMovimientoVaciaError(DomainError):
    def __init__(self):
        super().__init__(
            "La descripcion del movimiento no puede estar vacia.",
            code="MOV-012",
            category=ErrorCategory.VALIDATION,
        )


class UsuarioDestinoObligatorioError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar el usuario destino del movimiento.",
            code="MOV-013",
            category=ErrorCategory.VALIDATION,
        )


class EventoNombreObligatorioError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar el nombre del evento.",
            code="MOV-014",
            category=ErrorCategory.VALIDATION,
        )


class FechasMovimientoInvalidasError(DomainError):
    def __init__(self):
        super().__init__(
            "La fecha de retorno no puede ser anterior a la fecha de salida.",
            code="MOV-015",
            category=ErrorCategory.VALIDATION,
        )


class ActivosMovimientoObligatoriosError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar al menos un activo.",
            code="MOV-016",
            category=ErrorCategory.VALIDATION,
        )


class BajaDeUnSoloActivoError(DomainError):
    def __init__(self):
        super().__init__(
            "Una baja se solicita de a un activo.",
            code="MOV-017",
            category=ErrorCategory.VALIDATION,
        )


class SentidoPrestamoObligatorioError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe indicar si presta o solicita en prestamo.",
            code="MOV-018",
            category=ErrorCategory.VALIDATION,
        )


class NoEsResponsableDelActivoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"Solo puede prestar activos que tiene a su cargo; '{activo_id}' es de otra persona.",
            code="MOV-019",
            category=ErrorCategory.FORBIDDEN,
        )


class DestinatarioNoPermitidoError(DomainError):
    def __init__(self):
        super().__init__(
            "Solo un administrador general puede elegir otro destinatario; el activo se entrega a quien lo pide.",
            code="MOV-020",
            category=ErrorCategory.FORBIDDEN,
        )


class ActivoNoPerteneceAlMovimientoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no hace parte del movimiento.",
            code="MOV-021",
            category=ErrorCategory.VALIDATION,
        )


class SinActivosParaProcesarError(DomainError):
    def __init__(self):
        super().__init__(
            "No hay activos del movimiento sobre los que pueda ejecutar esta accion.",
            code="MOV-022",
            category=ErrorCategory.BUSINESS_RULE,
        )


class ObservacionDeNovedadObligatoriaError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"Debe describir la novedad del activo '{activo_id}'.",
            code="MOV-023",
            category=ErrorCategory.VALIDATION,
        )


class DestinatarioIgualAlResponsableError(DomainError):
    def __init__(self):
        super().__init__(
            "El destinatario del prestamo no puede ser quien lo presta.",
            code="MOV-024",
            category=ErrorCategory.VALIDATION,
        )
