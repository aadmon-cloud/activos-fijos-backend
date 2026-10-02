from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.datos_google_usuario_dto import DatosGoogleUsuarioDTO
from modules.auth.application.services.login_con_google import LoginConGoogleService
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import UsuarioInactivoError
from shared.domain.entities.audit_persona import AuditPersona


def _datos_google(email="ana@gmail.com", google_id="g-123", nombre="Ana Perez"):
    return DatosGoogleUsuarioDTO(
        email=email, google_id=google_id, nombre=nombre, picture="http://pic"
    )


def _usuario_existente(**overrides):
    base = dict(
        id="507f1f77bcf86cd799439011",
        email="ana@gmail.com",
        username="ana",
        password_hash="hash",
        google_id=None,
        google_picture=None,
        email_verificado=False,
        activo=True,
        creado_por=AuditPersona(
            id_persona="507f1f77bcf86cd799439011", nombre="ana", fecha=datetime.now(UTC)
        ),
    )
    base.update(overrides)
    return Usuario(**base)


@pytest.fixture
def usuario_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda usuario: usuario.model_copy(update={"id": "nuevo-id"})
    return mock


@pytest.fixture
def google_oauth_mock():
    mock = AsyncMock()
    mock.obtener_datos_usuario.return_value = _datos_google()
    return mock


@pytest.fixture
def token_port_mock():
    mock = MagicMock()
    mock.crear_token.return_value = "jwt-token"
    return mock


@pytest.fixture
def service(usuario_repository_mock, google_oauth_mock, token_port_mock):
    return LoginConGoogleService(usuario_repository_mock, google_oauth_mock, token_port_mock)


async def test_usuario_nuevo_se_crea_y_retorna_token(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_email.return_value = None
    usuario_repository_mock.obtener_por_google_id.return_value = None

    resultado = await service.ejecutar("code-123")

    usuario_repository_mock.crear.assert_called_once()
    usuario_creado = usuario_repository_mock.crear.call_args.args[0]
    assert usuario_creado.email == "ana@gmail.com"
    assert usuario_creado.password_hash is None
    assert usuario_creado.email_verificado is True
    assert resultado.access_token == "jwt-token"


async def test_usuario_nuevo_username_colisiona_agrega_sufijo(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = None
    usuario_repository_mock.obtener_por_google_id.return_value = None
    usuario_repository_mock.existe_por_username.return_value = True

    await service.ejecutar("code-123")

    usuario_creado = usuario_repository_mock.crear.call_args.args[0]
    assert usuario_creado.username != "ana_perez"
    assert usuario_creado.username.startswith("ana_perez_")


async def test_usuario_existente_por_email_sin_google_se_vincula(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = _usuario_existente()
    usuario_repository_mock.actualizar.side_effect = lambda usuario: usuario

    resultado = await service.ejecutar("code-123")

    usuario_repository_mock.actualizar.assert_called_once()
    usuario_vinculado = usuario_repository_mock.actualizar.call_args.args[0]
    assert usuario_vinculado.google_id == "g-123"
    assert usuario_vinculado.email_verificado is True
    usuario_repository_mock.crear.assert_not_called()
    assert resultado.access_token == "jwt-token"


async def test_usuario_existente_ya_vinculado_no_actualiza(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_email.return_value = _usuario_existente(
        google_id="g-123", google_picture="http://pic", email_verificado=True
    )

    await service.ejecutar("code-123")

    usuario_repository_mock.actualizar.assert_not_called()
    usuario_repository_mock.crear.assert_not_called()


async def test_usuario_encontrado_por_google_id_cuando_email_no_coincide(
    service, usuario_repository_mock
):
    usuario_repository_mock.obtener_por_email.return_value = None
    usuario_repository_mock.obtener_por_google_id.return_value = _usuario_existente(
        google_id="g-123", google_picture="http://pic", email_verificado=True
    )

    resultado = await service.ejecutar("code-123")

    usuario_repository_mock.crear.assert_not_called()
    assert resultado.access_token == "jwt-token"


async def test_usuario_inactivo_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_email.return_value = _usuario_existente(
        activo=False, google_id="g-123", google_picture="http://pic", email_verificado=True
    )

    with pytest.raises(UsuarioInactivoError):
        await service.ejecutar("code-123")
