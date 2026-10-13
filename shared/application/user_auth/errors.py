from shared.domain.errors import DomainError, ErrorCategory


class TokenUsuarioInvalidoError(Exception):
    def __init__(self, detalle: str):
        super().__init__(f"Token invalido: {detalle}")
        self.detalle = detalle


class SesionRequeridaError(DomainError):
    def __init__(self):
        super().__init__(
            "Se requiere una sesion activa.",
            code="AUTH-001",
            category=ErrorCategory.UNAUTHORIZED,
        )


class SesionInvalidaError(DomainError):
    def __init__(self):
        super().__init__(
            "La sesion no es valida o expiro.",
            code="AUTH-002",
            category=ErrorCategory.UNAUTHORIZED,
        )


class PermisosInsuficientesError(DomainError):
    def __init__(self):
        super().__init__(
            "No tiene permisos para esta accion.",
            code="AUTH-003",
            category=ErrorCategory.FORBIDDEN,
        )


class CabeceraCsrfFaltanteError(DomainError):
    def __init__(self):
        super().__init__(
            "Falta la cabecera de proteccion CSRF.",
            code="AUTH-004",
            category=ErrorCategory.FORBIDDEN,
        )
