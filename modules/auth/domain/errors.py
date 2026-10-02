from shared.domain.errors import DomainError, ErrorCategory


class CredencialesInvalidasError(DomainError):
    def __init__(self):
        super().__init__(
            message="Email o contraseña incorrectos.",
            code="AUTH-001",
            category=ErrorCategory.UNAUTHORIZED,
        )


class UsuarioInactivoError(DomainError):
    def __init__(self, usuario_id: str):
        super().__init__(
            message="El usuario está desactivado. Contacte al administrador.",
            code="AUTH-002",
            category=ErrorCategory.FORBIDDEN,
            details={"usuario_id": usuario_id},
        )


class EmailYaRegistradoError(DomainError):
    def __init__(self, email: str):
        super().__init__(
            message=f"El email '{email}' ya está registrado.",
            code="AUTH-003",
            category=ErrorCategory.CONFLICT,
            details={"email": email},
        )


class ConfirmacionPasswordInvalidaError(DomainError):
    def __init__(self):
        super().__init__(
            message="Las contraseñas no coinciden.",
            code="AUTH-004",
            category=ErrorCategory.VALIDATION,
        )


class TokenInvalidoError(DomainError):
    def __init__(self):
        super().__init__(
            message="Token inválido o expirado.",
            code="AUTH-005",
            category=ErrorCategory.UNAUTHORIZED,
        )


class UsuarioNoEncontradoError(DomainError):
    def __init__(self, usuario_id: str):
        super().__init__(
            message="El usuario del token ya no existe.",
            code="AUTH-006",
            category=ErrorCategory.UNAUTHORIZED,
            details={"usuario_id": usuario_id},
        )


class PermisoInsuficienteError(DomainError):
    def __init__(self, roles_permitidos: list[str]):
        super().__init__(
            message=f"Se requiere uno de los siguientes roles: {', '.join(roles_permitidos)}.",
            code="AUTH-007",
            category=ErrorCategory.FORBIDDEN,
            details={"roles_permitidos": roles_permitidos},
        )


class TokenRecuperacionInvalidoError(DomainError):
    def __init__(self):
        super().__init__(
            message="Token inválido o expirado.",
            code="AUTH-008",
            category=ErrorCategory.VALIDATION,
        )


class PasswordActualIncorrectaError(DomainError):
    def __init__(self):
        super().__init__(
            message="La contraseña actual es incorrecta.",
            code="AUTH-009",
            category=ErrorCategory.UNAUTHORIZED,
        )


class GoogleOAuthError(DomainError):
    def __init__(self, detalle: str):
        super().__init__(
            message=f"Error en la autenticación con Google: {detalle}",
            code="AUTH-010",
            category=ErrorCategory.INTEGRATION,
            details={"detalle": detalle},
        )


class GoogleOAuthNoConfiguradoError(DomainError):
    def __init__(self):
        super().__init__(
            message="Google OAuth no está configurado en el servidor.",
            code="AUTH-011",
            category=ErrorCategory.INTERNAL,
        )


class UsuarioAdminNoEncontradoError(DomainError):
    """Distinto de UsuarioNoEncontradoError (401, contexto JWT): esta es la
    búsqueda por id que hace un super_admin al editar/eliminar un usuario —
    semánticamente 404, no 401 (el admin sí está autorizado; el recurso no existe)."""

    def __init__(self, usuario_id: str):
        super().__init__(
            message=f"No existe un usuario con id '{usuario_id}'.",
            code="AUTH-012",
            category=ErrorCategory.NOT_FOUND,
            details={"usuario_id": usuario_id},
        )


class OperacionSobrePropioUsuarioNoPermitidaError(DomainError):
    def __init__(self):
        super().__init__(
            message="No puedes realizar esta operación sobre tu propio usuario.",
            code="AUTH-013",
            category=ErrorCategory.VALIDATION,
        )
