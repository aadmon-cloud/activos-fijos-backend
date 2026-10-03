from shared.domain.errors import DomainError, ErrorCategory


class EmailYaRegistradoError(DomainError):
    def __init__(self, email: str):
        super().__init__(
            f"Ya existe un usuario registrado con el email '{email}'.",
            code="USR-001",
            category=ErrorCategory.CONFLICT,
        )


class IdentificacionYaRegistradaError(DomainError):
    def __init__(self, identificacion: str):
        super().__init__(
            f"Ya existe un usuario registrado con la identificacion '{identificacion}'.",
            code="USR-002",
            category=ErrorCategory.CONFLICT,
        )


class PasswordDebilError(DomainError):
    def __init__(self):
        super().__init__(
            "La contrasena debe tener al menos 8 caracteres.",
            code="USR-003",
            category=ErrorCategory.VALIDATION,
        )


class CredencialesInvalidasError(DomainError):
    def __init__(self):
        super().__init__(
            "El email o la contrasena son incorrectos.",
            code="USR-004",
            category=ErrorCategory.UNAUTHORIZED,
        )


class UsuarioNoEncontradoError(DomainError):
    def __init__(self, id_usuario: str):
        super().__init__(
            f"El usuario '{id_usuario}' no existe.",
            code="USR-005",
            category=ErrorCategory.NOT_FOUND,
        )


class AreaInvalidaError(DomainError):
    def __init__(self, area_id: str):
        super().__init__(
            f"El area '{area_id}' no existe.",
            code="USR-006",
            category=ErrorCategory.VALIDATION,
        )
