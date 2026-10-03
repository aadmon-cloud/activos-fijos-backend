from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.usuarios.application.dto.login_dto import LoginDTO
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import CredencialesInvalidasError
from shared.domain.entities.audit import AuditPersona


def _usuario(**overrides) -> Usuario:
    valores = dict(
        id="1",
        email="ana@example.com",
        nombre="Ana",
        apellido="Garcia",
        password_hash="hash",
        rol=RolUsuario.EMPLEADO,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Usuario(**valores)


@pytest.fixture
def repositorio_mock():
    return AsyncMock()


@pytest.fixture
def hasher_mock():
    return MagicMock()


@pytest.fixture
def emisor_token_mock():
    mock = MagicMock()
    mock.emitir.return_value = "token-emitido"
    return mock


async def test_autenticar_usuario_retorna_token_si_las_credenciales_son_validas(
    repositorio_mock, hasher_mock, emisor_token_mock
):
    repositorio_mock.obtener_por_email.return_value = _usuario()
    hasher_mock.verificar.return_value = True
    service = AutenticarUsuarioService(repositorio_mock, hasher_mock, emisor_token_mock)

    resultado = await service.ejecutar(
        LoginDTO(email="Ana@Example.com", password="password123")
    )

    assert resultado.access_token == "token-emitido"
    assert resultado.usuario.email == "ana@example.com"


async def test_autenticar_usuario_lanza_error_si_el_usuario_no_existe(
    repositorio_mock, hasher_mock, emisor_token_mock
):
    repositorio_mock.obtener_por_email.return_value = None
    service = AutenticarUsuarioService(repositorio_mock, hasher_mock, emisor_token_mock)

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginDTO(email="ana@example.com", password="password123"))


async def test_autenticar_usuario_lanza_error_si_la_password_no_coincide(
    repositorio_mock, hasher_mock, emisor_token_mock
):
    repositorio_mock.obtener_por_email.return_value = _usuario()
    hasher_mock.verificar.return_value = False
    service = AutenticarUsuarioService(repositorio_mock, hasher_mock, emisor_token_mock)

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginDTO(email="ana@example.com", password="incorrecta"))


async def test_autenticar_usuario_lanza_error_si_el_usuario_esta_inactivo(
    repositorio_mock, hasher_mock, emisor_token_mock
):
    repositorio_mock.obtener_por_email.return_value = _usuario(activo=False)
    hasher_mock.verificar.return_value = True
    service = AutenticarUsuarioService(repositorio_mock, hasher_mock, emisor_token_mock)

    with pytest.raises(CredencialesInvalidasError):
        await service.ejecutar(LoginDTO(email="ana@example.com", password="password123"))
