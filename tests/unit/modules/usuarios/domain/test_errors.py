from modules.usuarios.domain.errors import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    IdentificacionYaRegistradaError,
    PasswordDebilError,
    UsuarioNoEncontradoError,
)
from shared.domain.errors import ErrorCategory


def test_email_ya_registrado_error_tiene_code_category_y_mensaje():
    error = EmailYaRegistradoError("ana@example.com")

    assert error.code == "USR-001"
    assert error.category == ErrorCategory.CONFLICT
    assert "ana@example.com" in error.message


def test_identificacion_ya_registrada_error_tiene_code_y_category():
    error = IdentificacionYaRegistradaError("123")

    assert error.code == "USR-002"
    assert error.category == ErrorCategory.CONFLICT


def test_password_debil_error_tiene_code_y_category():
    error = PasswordDebilError()

    assert error.code == "USR-003"
    assert error.category == ErrorCategory.VALIDATION


def test_credenciales_invalidas_error_tiene_code_y_category():
    error = CredencialesInvalidasError()

    assert error.code == "USR-004"
    assert error.category == ErrorCategory.UNAUTHORIZED


def test_usuario_no_encontrado_error_tiene_code_category_y_mensaje():
    error = UsuarioNoEncontradoError("123")

    assert error.code == "USR-005"
    assert error.category == ErrorCategory.NOT_FOUND
    assert "123" in error.message
