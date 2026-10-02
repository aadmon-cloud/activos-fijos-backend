from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordInput,
)
from modules.auth.application.services.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordService,
)
from modules.auth.domain.entities.usuario import Usuario
from shared.domain.entities.audit_persona import AuditPersona


def _usuario():
    return Usuario(
        id="507f1f77bcf86cd799439011",
        email="ana@example.com",
        username="ana",
        password_hash="hash",
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439011", nombre="ana", fecha=datetime.now(UTC)
        ),
    )


@pytest.fixture
def usuario_repository_mock():
    return AsyncMock()


@pytest.fixture
def email_sender_mock():
    mock = MagicMock()
    mock.enviar_recuperacion_password.return_value = True
    return mock


@pytest.fixture
def service(usuario_repository_mock, email_sender_mock):
    return SolicitarRecuperacionPasswordService(usuario_repository_mock, email_sender_mock)


async def test_usuario_existente_genera_token_y_envia_email(
    service, usuario_repository_mock, email_sender_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario()

    await service.ejecutar(SolicitarRecuperacionPasswordInput(email="ANA@example.com"))

    usuario_repository_mock.actualizar.assert_called_once()
    usuario_actualizado = usuario_repository_mock.actualizar.call_args.args[0]
    assert usuario_actualizado.reset_password_token is not None
    assert usuario_actualizado.reset_password_expires is not None
    email_sender_mock.enviar_recuperacion_password.assert_called_once_with(
        "ana@example.com", usuario_actualizado.reset_password_token
    )


async def test_usuario_inexistente_no_hace_nada_ni_lanza_error(
    service, usuario_repository_mock, email_sender_mock
):
    usuario_repository_mock.obtener_por_email.return_value = None

    await service.ejecutar(SolicitarRecuperacionPasswordInput(email="nadie@example.com"))

    usuario_repository_mock.actualizar.assert_not_called()
    email_sender_mock.enviar_recuperacion_password.assert_not_called()


async def test_fallo_de_envio_de_email_no_propaga_error(
    service, usuario_repository_mock, email_sender_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario()
    email_sender_mock.enviar_recuperacion_password.return_value = False

    await service.ejecutar(SolicitarRecuperacionPasswordInput(email="ana@example.com"))

    usuario_repository_mock.actualizar.assert_called_once()
