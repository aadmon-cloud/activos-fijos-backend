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


class PasswordActualIncorrectaError(DomainError):
    def __init__(self):
        super().__init__(
            "La contrasena actual es incorrecta.",
            code="USR-007",
            category=ErrorCategory.VALIDATION,
        )


class PasswordNuevaIgualALaActualError(DomainError):
    def __init__(self):
        super().__init__(
            "La contrasena nueva debe ser distinta de la actual.",
            code="USR-008",
            category=ErrorCategory.BUSINESS_RULE,
        )


class TokenGoogleInvalidoError(DomainError):
    def __init__(self):
        super().__init__(
            "No se pudo validar el ingreso con Google. Intenta de nuevo.",
            code="USR-009",
            category=ErrorCategory.UNAUTHORIZED,
        )


class CuentaGoogleSinAccesoError(DomainError):
    def __init__(self):
        super().__init__(
            "Esta cuenta de Google no tiene acceso al sistema. Pide al administrador que te registre.",
            code="USR-010",
            category=ErrorCategory.UNAUTHORIZED,
        )


class IngresoConGoogleNoConfiguradoError(DomainError):
    def __init__(self):
        super().__init__(
            "El ingreso con Google no esta configurado.",
            code="USR-011",
            category=ErrorCategory.INTEGRATION,
        )


class LoginConPasswordDeshabilitadoError(DomainError):
    def __init__(self):
        super().__init__(
            "El ingreso con contrasena esta deshabilitado. Ingresa con tu cuenta de Google.",
            code="USR-012",
            category=ErrorCategory.FORBIDDEN,
        )

