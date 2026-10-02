from shared.domain.errors import DomainError, ErrorCategory


class TituloTareaInvalidoError(DomainError):
    def __init__(self):
        super().__init__(
            message="El titulo de la tarea es obligatorio.",
            code="EJEMPLO-TAREAS-001",
            category=ErrorCategory.VALIDATION,
        )


class TareaNoEncontradaError(DomainError):
    def __init__(self, tarea_id: str):
        super().__init__(
            message=f"No existe una tarea con id '{tarea_id}'.",
            code="EJEMPLO-TAREAS-002",
            category=ErrorCategory.NOT_FOUND,
            details={"tarea_id": tarea_id},
        )


class TareaYaCompletadaError(DomainError):
    def __init__(self, tarea_id: str):
        super().__init__(
            message=f"La tarea '{tarea_id}' ya estaba completada.",
            code="EJEMPLO-TAREAS-003",
            category=ErrorCategory.CONFLICT,
            details={"tarea_id": tarea_id},
        )
