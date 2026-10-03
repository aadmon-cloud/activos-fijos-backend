from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.usuarios.application.dto.desactivar_usuario_dto import DesactivarUsuarioDTO
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import UsuarioNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _usuario(activo: bool = True) -> Usuario:
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


async def test_desactivar_usuario_marca_activo_en_false():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario()
    service = DesactivarUsuarioService(repositorio_mock)

    await service.ejecutar(
        DesactivarUsuarioDTO(id_usuario="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
    )

    usuario_guardado = repositorio_mock.guardar.call_args.args[0]
    assert usuario_guardado.activo is False


async def test_desactivar_usuario_es_idempotente_si_ya_esta_inactivo():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = _usuario(activo=False)
    service = DesactivarUsuarioService(repositorio_mock)

    await service.ejecutar(
        DesactivarUsuarioDTO(id_usuario="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
    )

    repositorio_mock.guardar.assert_not_called()


async def test_desactivar_usuario_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = DesactivarUsuarioService(repositorio_mock)

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar(
            DesactivarUsuarioDTO(
                id_usuario="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )
