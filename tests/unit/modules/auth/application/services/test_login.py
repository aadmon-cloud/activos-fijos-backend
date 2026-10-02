from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.login import LoginInput
from modules.auth.application.services.login import LoginService
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import CredencialesInvalidasError, UsuarioInactivoError
from shared.domain.entities.audit_persona import AuditPersona


def _usuario(activo=True, password_hash="hash-valido"):
    return Usuario(
        id="507f1f77bcf86cd799439011",
        email="ana@example.com",
        username="ana",
        password_hash=password_hash,
        activo=activo,
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439011",
            nombre="ana",
            fecha=datetime.now(UTC),
        ),
    )


@pytest.fixture
def usuario_repository_mock():
    return AsyncMock()


@pytest.fixture
def password_hasher_mock():
    mock = MagicMock()
    mock.verificar.return_value = True
    return mock


@pytest.fixture
def token_port_mock():
    mock = MagicMock()
    mock.crear_token.return_value = "token-jwt"
    return mock


@pytest.fixture
def service(usuario_repository_mock, password_hasher_mock, token_port_mock):
    return LoginService(usuario_repository_mock, password_hasher_mock, token_port_mock)


async def test_login_exitoso_retorna_token(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario()

    resultado = await service.ejecutar(LoginInput(email="ANA@example.com", password="clave12345"))

    assert resultado.access_token == "token-jwt"
    assert resultado.usuario.email == "ana@example.com"
    usuario_repository_mock.obtener_por_email.assert_called_once_with("ana@example.com")


async def test_login_usuario_no_encontrado_lanza_credenciales_invalidas(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = None

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginInput(email="nadie@example.com", password="clave12345"))


async def test_login_password_incorrecto_lanza_credenciales_invalidas(
    service, usuario_repository_mock, password_hasher_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario()
    password_hasher_mock.verificar.return_value = False

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginInput(email="ana@example.com", password="incorrecta"))


async def test_login_cuenta_solo_google_sin_password_lanza_credenciales_invalidas(
    service, usuario_repository_mock, password_hasher_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario(password_hash=None)

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginInput(email="ana@example.com", password="clave12345"))

    password_hasher_mock.verificar.assert_not_called()


async def test_login_usuario_inactivo_lanza_usuario_inactivo(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario(activo=False)

    with pytest.raises(UsuarioInactivoError):
        await service.ejecutar(LoginInput(email="ana@example.com", password="clave12345"))
