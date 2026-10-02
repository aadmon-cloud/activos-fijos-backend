from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.restablecer_password import RestablecerPasswordInput
from modules.auth.application.services.restablecer_password import (
    RestablecerPasswordService,
)
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    TokenRecuperacionInvalidoError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _usuario_con_token(token="tok-valido", expira_en_horas=1):
    ahora = datetime.now(UTC)
    return Usuario(
        id="507f1f77bcf86cd799439011",
        email="ana@example.com",
        username="ana",
        password_hash="hash-viejo",
        reset_password_token=token,
        reset_password_expires=ahora + timedelta(hours=expira_en_horas),
        creado_por=AuditPersona(id_persona="507f1f77bcf86cd799439011", nombre="ana", fecha=ahora),
    )


@pytest.fixture
def usuario_repository_mock():
    return AsyncMock()


@pytest.fixture
def password_hasher_mock():
    mock = MagicMock()
    mock.hashear.return_value = "hash-nuevo"
    return mock


@pytest.fixture
def service(usuario_repository_mock, password_hasher_mock):
    return RestablecerPasswordService(usuario_repository_mock, password_hasher_mock)


async def test_token_valido_actualiza_password_y_limpia_token(
    service, usuario_repository_mock, password_hasher_mock
):
    usuario_repository_mock.obtener_por_token_reset.return_value = _usuario_con_token()

    await service.ejecutar(
        RestablecerPasswordInput(
            token="tok-valido", new_password="clave1234", confirm_password="clave1234"
        )
    )

    usuario_repository_mock.actualizar.assert_called_once()
    usuario_actualizado = usuario_repository_mock.actualizar.call_args.args[0]
    assert usuario_actualizado.password_hash == "hash-nuevo"
    assert usuario_actualizado.reset_password_token is None
    assert usuario_actualizado.reset_password_expires is None


async def test_passwords_no_coinciden_lanza_error_sin_tocar_repositorio(
    service, usuario_repository_mock
):
    with pytest.raises(ConfirmacionPasswordInvalidaError):
        await service.ejecutar(
            RestablecerPasswordInput(
                token="tok-valido", new_password="clave1234", confirm_password="otraclave"
            )
        )

    usuario_repository_mock.obtener_por_token_reset.assert_not_called()


async def test_token_inexistente_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_token_reset.return_value = None

    with pytest.raises(TokenRecuperacionInvalidoError):
        await service.ejecutar(
            RestablecerPasswordInput(
                token="no-existe", new_password="clave1234", confirm_password="clave1234"
            )
        )


async def test_token_expirado_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_token_reset.return_value = _usuario_con_token(
        expira_en_horas=-1
    )

    with pytest.raises(TokenRecuperacionInvalidoError):
        await service.ejecutar(
            RestablecerPasswordInput(
                token="tok-valido", new_password="clave1234", confirm_password="clave1234"
            )
        )
