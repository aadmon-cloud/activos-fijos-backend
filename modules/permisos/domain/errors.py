from shared.domain.errors import DomainError, ErrorCategory


class RolDesconocidoError(DomainError):
    def __init__(self, rol: str):
        super().__init__(
            f"El rol '{rol}' no existe.",
            code="PER-001",
            category=ErrorCategory.NOT_FOUND,
        )


class RolNoEditableError(DomainError):
    def __init__(self, rol: str):
        super().__init__(
            f"Los permisos del rol '{rol}' no se pueden editar: siempre tiene todas las funciones.",
            code="PER-002",
            category=ErrorCategory.BUSINESS_RULE,
        )


class PermisoDesconocidoError(DomainError):
    def __init__(self, permiso: str):
        super().__init__(
            f"La funcion '{permiso}' no existe.",
            code="PER-003",
            category=ErrorCategory.VALIDATION,
        )


class PermisoBaseNoDeshabilitableError(DomainError):
    def __init__(self, permiso: str):
        super().__init__(
            f"La funcion '{permiso}' es basica: todo rol la necesita para entrar al sistema y no se puede deshabilitar.",
            code="PER-004",
            category=ErrorCategory.BUSINESS_RULE,
        )
