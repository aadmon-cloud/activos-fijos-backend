from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.crear_usuario_admin import CrearUsuarioAdminInput
from modules.auth.application.services.crear_usuario_admin import CrearUsuarioAdminService
from modules.auth.domain.entities.usuario import RolUsuario, Usuario
from modules.auth.domain.errors import EmailYaRegistradoError
from shared.domain.entities.audit_persona import AuditPersona


def _admin():
    return Usuario(
        id="admin-id",
        email="admin@example.com",
        username="admin",
        rol=RolUsuario.SUPER_ADMIN,
        creado_por=AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC)),
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
    return CrearUsuarioAdminService(usuario_repository_mock, password_hasher_mock)


async def test_crea_usuario_con_rol_explicito(service, usuario_repository_mock):
    entrada = CrearUsuarioAdminInput(email="nuevo@example.com", rol=RolUsuario.ADMIN)

    usuario = await service.ejecutar(_admin(), entrada)

    assert usuario.rol == RolUsuario.ADMIN
    assert usuario.creado_por.id_persona == "admin-id"


async def test_sin_password_queda_sin_hash(service, usuario_repository_mock, password_hasher_mock):
    entrada = CrearUsuarioAdminInput(email="nuevo@example.com")

    usuario = await service.ejecutar(_admin(), entrada)

    assert usuario.password_hash is None
    password_hasher_mock.hashear.assert_not_called()


async def test_con_password_se_hashea(service, password_hasher_mock):
    entrada = CrearUsuarioAdminInput(email="nuevo@example.com", password="clave1234")

    usuario = await service.ejecutar(_admin(), entrada)

    assert usuario.password_hash == "hash-seguro"
    password_hasher_mock.hashear.assert_called_once_with("clave1234")


async def test_email_duplicado_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.existe_por_email.return_value = True
    entrada = CrearUsuarioAdminInput(email="dup@example.com")

    with pytest.raises(EmailYaRegistradoError):
        await service.ejecutar(_admin(), entrada)


async def test_username_colisiona_agrega_sufijo(service, usuario_repository_mock):
    usuario_repository_mock.existe_por_username.return_value = True
    entrada = CrearUsuarioAdminInput(email="nuevo@example.com")

    usuario = await service.ejecutar(_admin(), entrada)

    assert usuario.username.startswith("nuevo_")
