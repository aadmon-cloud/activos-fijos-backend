from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.registrar_usuario import RegistrarUsuarioInput
from modules.auth.application.services.registrar_usuario import RegistrarUsuarioService
from modules.auth.domain.entities.usuario import RolUsuario
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    EmailYaRegistradoError,
)


@pytest.fixture
def usuario_repository_mock():
    mock = AsyncMock()
    mock.existe_por_email.return_value = False
    mock.existe_por_username.return_value = False
    mock.crear.side_effect = lambda usuario: usuario.model_copy(update={"id": "nuevo-id"})
    return mock


@pytest.fixture
def password_hasher_mock():
    mock = MagicMock()
    mock.hashear.return_value = "hash-seguro"
    return mock


@pytest.fixture
def service(usuario_repository_mock, password_hasher_mock):
    return RegistrarUsuarioService(usuario_repository_mock, password_hasher_mock)


async def test_registrar_usuario_exitoso(service, password_hasher_mock):
    entrada = RegistrarUsuarioInput(
        email="Nuevo@Example.com",
        password="clave1234",
        confirm_password="clave1234",
    )

    usuario = await service.ejecutar(entrada)

    assert usuario.email == "nuevo@example.com"
    assert usuario.username == "nuevo"
    assert usuario.rol == RolUsuario.OPERATIVO
    assert usuario.id == "nuevo-id"
    password_hasher_mock.hashear.assert_called_once_with("clave1234")


async def test_registrar_usuario_passwords_no_coinciden(service, usuario_repository_mock):
    entrada = RegistrarUsuarioInput(
        email="a@example.com", password="clave1234", confirm_password="otraclave"
    )

    with pytest.raises(ConfirmacionPasswordInvalidaError):
        await service.ejecutar(entrada)

    usuario_repository_mock.existe_por_email.assert_not_called()


async def test_registrar_usuario_email_duplicado(service, usuario_repository_mock):
    usuario_repository_mock.existe_por_email.return_value = True
    entrada = RegistrarUsuarioInput(
        email="dup@example.com", password="clave1234", confirm_password="clave1234"
    )

    with pytest.raises(EmailYaRegistradoError):
        await service.ejecutar(entrada)


async def test_registrar_usuario_username_colisiona_agrega_sufijo(
    service, usuario_repository_mock
):
    usuario_repository_mock.existe_por_username.return_value = True
    entrada = RegistrarUsuarioInput(
        email="ana@example.com", password="clave1234", confirm_password="clave1234"
    )

    usuario = await service.ejecutar(entrada)

    assert usuario.username != "ana"
    assert usuario.username.startswith("ana_")
