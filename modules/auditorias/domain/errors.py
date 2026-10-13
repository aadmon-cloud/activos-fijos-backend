from shared.domain.errors import DomainError, ErrorCategory


class UsuarioNoEncontradoParaAuditoriaError(DomainError):
    def __init__(self, usuario_id: str):
        super().__init__(
            f"El usuario '{usuario_id}' no existe.",
            code="AUD-001",
            category=ErrorCategory.NOT_FOUND,
        )


class AuditoriaNoModificableError(DomainError):
    def __init__(self, id_auditoria: str):
        super().__init__(
            f"La auditoria '{id_auditoria}' ya fue cerrada y no se puede modificar.",
            code="AUD-002",
            category=ErrorCategory.BUSINESS_RULE,
        )


class ItemAuditoriaNoEncontradoError(DomainError):
    def __init__(self, activo_id: str):
        super().__init__(
            f"El activo '{activo_id}' no forma parte de esta auditoria.",
            code="AUD-003",
            category=ErrorCategory.NOT_FOUND,
        )


class ObservacionObligatoriaError(DomainError):
    def __init__(self):
        super().__init__(
            "Debe registrar una observacion cuando el resultado es 'encontrado_con_novedad'.",
            code="AUD-004",
            category=ErrorCategory.VALIDATION,
        )


class AuditoriaNoEncontradaError(DomainError):
    def __init__(self, id_auditoria: str):
        super().__init__(
            f"La auditoria '{id_auditoria}' no existe.",
            code="AUD-005",
            category=ErrorCategory.NOT_FOUND,
        )


class PdfAuditoriaNoDisponibleError(DomainError):
    def __init__(self, id_auditoria: str):
        super().__init__(
            f"La auditoria '{id_auditoria}' aun no tiene un PDF generado.",
            code="AUD-006",
            category=ErrorCategory.NOT_FOUND,
        )
