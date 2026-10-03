from shared.domain.errors import DomainError, ErrorCategory


class TituloTareaVacioError(DomainError):
    def __init__(self):
        super().__init__(
            "El titulo de la tarea no puede estar vacio.",
            code="TAR-001",
            category=ErrorCategory.BUSINESS_RULE,
        )
