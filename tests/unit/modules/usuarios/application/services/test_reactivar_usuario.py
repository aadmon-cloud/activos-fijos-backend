from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.usuarios.application.dto.reactivar_usuario_dto import ReactivarUsuarioDTO
from modules.usuarios.application.services.reactivar_usuario import ReactivarUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import UsuarioNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _usuario(activo: bool) -> Usuario:
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
        activo=activo,
        creado_por=AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _dto() -> ReactivarUsuarioDTO:
    return ReactivarUsuarioDTO(id_usuario="1", actualizado_por_id="9", actualizado_por_nombre="Admin")


async def test_reactivar_usuario_marca_activo_en_true_y_audita():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario(activo=False)
    service = ReactivarUsuarioService(repositorio_mock)

    await service.ejecutar(_dto())

    guardado = repositorio_mock.guardar.call_args.args[0]
    assert guardado.activo is True
    assert guardado.actualizado_por.id_persona == "9"


async def test_reactivar_usuario_es_idempotente_si_ya_esta_activo():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario(activo=True)
    service = ReactivarUsuarioService(repositorio_mock)

    await service.ejecutar(_dto())

    repositorio_mock.guardar.assert_not_called()


async def test_reactivar_usuario_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ReactivarUsuarioService(repositorio_mock)

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar(_dto())
