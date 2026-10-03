from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import UsuarioNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _usuario() -> Usuario:
    return Usuario(
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


async def test_obtener_usuario_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario()
    service = ObtenerUsuarioService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.email == "ana@example.com"


async def test_obtener_usuario_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerUsuarioService(repositorio_mock)

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar("1")
