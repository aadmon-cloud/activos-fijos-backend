from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auth.application.services.eliminar_usuario_admin import (
    EliminarUsuarioAdminService,
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


@pytest.fixture
def usuario_repository_mock():
    mock = AsyncMock()
    mock.eliminar.return_value = True
    return mock


@pytest.fixture
def service(usuario_repository_mock):
    return EliminarUsuarioAdminService(usuario_repository_mock)


async def test_elimina_usuario(service, usuario_repository_mock):
    await service.ejecutar(_admin(), "target-id")

    usuario_repository_mock.eliminar.assert_called_once_with("target-id")


async def test_no_permite_eliminarse_a_si_mismo(service, usuario_repository_mock):
    with pytest.raises(OperacionSobrePropioUsuarioNoPermitidaError):
        await service.ejecutar(_admin(), "admin-id")

    usuario_repository_mock.eliminar.assert_not_called()


async def test_usuario_inexistente_lanza_error(service, usuario_repository_mock):
    usuario_repository_mock.eliminar.return_value = False

    with pytest.raises(UsuarioAdminNoEncontradoError):
        await service.ejecutar(_admin(), "no-existe")
