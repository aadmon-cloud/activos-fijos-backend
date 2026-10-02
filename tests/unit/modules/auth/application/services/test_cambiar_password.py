from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.cambiar_password import CambiarPasswordInput
from modules.auth.application.services.cambiar_password import CambiarPasswordService
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    PasswordActualIncorrectaError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _usuario(password_hash="hash-viejo"):
    return Usuario(
        id="507f1f77bcf86cd799439011",
        email="ana@example.com",
        username="ana",
        password_hash=password_hash,
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439011", nombre="ana", fecha=datetime.now(UTC)
        ),
    )


@pytest.fixture
def usuario_repository_mock():
    return AsyncMock()


@pytest.fixture
def password_hasher_mock():
    mock = MagicMock()
    mock.verificar.return_value = True
    mock.hashear.return_value = "hash-nuevo"
    return mock


@pytest.fixture
def service(usuario_repository_mock, password_hasher_mock):
    return CambiarPasswordService(usuario_repository_mock, password_hasher_mock)


async def test_cambio_exitoso_actualiza_hash(
    service, usuario_repository_mock, password_hasher_mock
):
    await service.ejecutar(
        _usuario(),
        CambiarPasswordInput(
            current_password="actual123", new_password="nueva1234", confirm_password="nueva1234"
        ),
    )

    usuario_repository_mock.actualizar.assert_called_once()
    usuario_actualizado = usuario_repository_mock.actualizar.call_args.args[0]
    assert usuario_actualizado.password_hash == "hash-nuevo"


async def test_passwords_nuevas_no_coinciden(service, usuario_repository_mock, password_hasher_mock):
    with pytest.raises(ConfirmacionPasswordInvalidaError):
        await service.ejecutar(
            _usuario(),
            CambiarPasswordInput(
                current_password="actual123",
                new_password="nueva1234",
                confirm_password="diferente1",
            ),
        )

    password_hasher_mock.verificar.assert_not_called()
    usuario_repository_mock.actualizar.assert_not_called()


async def test_password_actual_incorrecta(service, usuario_repository_mock, password_hasher_mock):
    password_hasher_mock.verificar.return_value = False

    with pytest.raises(PasswordActualIncorrectaError):
        await service.ejecutar(
            _usuario(),
            CambiarPasswordInput(
                current_password="incorrecta", new_password="nueva1234", confirm_password="nueva1234"
            ),
        )

    usuario_repository_mock.actualizar.assert_not_called()


async def test_cuenta_sin_password_lanza_error_sin_llamar_al_hasher(
    service, usuario_repository_mock, password_hasher_mock
):
    with pytest.raises(PasswordActualIncorrectaError):
        await service.ejecutar(
            _usuario(password_hash=None),
            CambiarPasswordInput(
                current_password="cualquiera", new_password="nueva1234", confirm_password="nueva1234"
            ),
        )

    password_hasher_mock.verificar.assert_not_called()
