from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.auth.application.dto.actualizar_usuario_admin import (
    ActualizarUsuarioAdminInput,
)
from modules.auth.application.services.actualizar_usuario_admin import (
    ActualizarUsuarioAdminService,
)
from modules.auth.domain.entities.usuario import RolUsuario, Usuario
from modules.auth.domain.errors import (
    OperacionSobrePropioUsuarioNoPermitidaError,
    UsuarioAdminNoEncontradoError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _admin():
    return Usuario(
        id="admin-id",
        email="admin@example.com",
        username="admin",
        rol=RolUsuario.SUPER_ADMIN,
        creado_por=AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC)),
    )


def _usuario_objetivo():
    return Usuario(
        id="target-id",
        email="target@example.com",
        username="target",
        rol=RolUsuario.OPERATIVO,
        activo=True,
        creado_por=AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def usuario_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _usuario_objetivo()
    mock.actualizar.side_effect = lambda usuario: usuario
    return mock


@pytest.fixture
def password_hasher_mock():
    mock = MagicMock()
    mock.hashear.return_value = "hash-nuevo"
    return mock


@pytest.fixture
def service(usuario_repository_mock, password_hasher_mock):
    return ActualizarUsuarioAdminService(usuario_repository_mock, password_hasher_mock)


async def test_actualiza_solo_campos_provistos(service, usuario_repository_mock):
    entrada = ActualizarUsuarioAdminInput(activo=False)

    usuario = await service.ejecutar(_admin(), "target-id", entrada)

    assert usuario.activo is False
    assert usuario.rol == RolUsuario.OPERATIVO
    assert usuario.username == "target"


async def test_actualiza_password_si_se_provee(service, password_hasher_mock):
    entrada = ActualizarUsuarioAdminInput(password="clave1234")

    usuario = await service.ejecutar(_admin(), "target-id", entrada)

    assert usuario.password_hash == "hash-nuevo"


async def test_no_permite_editarse_a_si_mismo(service):
    entrada = ActualizarUsuarioAdminInput(activo=False)

    with pytest.raises(OperacionSobrePropioUsuarioNoPermitidaError):
        await service.ejecutar(_admin(), "admin-id", entrada)


async def test_usuario_inexistente_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.obtener_por_id.return_value = None
    entrada = ActualizarUsuarioAdminInput(activo=False)

    with pytest.raises(UsuarioAdminNoEncontradoError):
        await service.ejecutar(_admin(), "no-existe", entrada)
