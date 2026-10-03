from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.usuarios.application.dto.actualizar_usuario_dto import ActualizarUsuarioDTO
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.domain.errors import AreaInvalidaError, UsuarioNoEncontradoError
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


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _usuario()
    mock.guardar.side_effect = lambda usuario: usuario
    return mock


@pytest.fixture
def verificador_area_mock():
    mock = AsyncMock()
    mock.existe.return_value = True
    return mock


async def test_actualizar_usuario_cambia_solo_los_campos_enviados(
    repositorio_mock, verificador_area_mock
):
    service = ActualizarUsuarioService(repositorio_mock, verificador_area_mock)

    resultado = await service.ejecutar(
        ActualizarUsuarioDTO(
            id_usuario="1",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
            rol=RolUsuario.JEFE_AREA,
        )
    )

    assert resultado.rol == "jefe_area"
    assert resultado.nombre == "Ana"
    usuario_guardado = repositorio_mock.guardar.call_args.args[0]
    assert usuario_guardado.actualizado_por.id_persona == "9"


async def test_actualizar_usuario_lanza_error_si_no_existe(
    repositorio_mock, verificador_area_mock
):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarUsuarioService(repositorio_mock, verificador_area_mock)

    with pytest.raises(UsuarioNoEncontradoError):
        await service.ejecutar(
            ActualizarUsuarioDTO(
                id_usuario="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )


async def test_actualizar_usuario_lanza_error_si_el_area_no_existe(
    repositorio_mock, verificador_area_mock
):
    verificador_area_mock.existe.return_value = False
    service = ActualizarUsuarioService(repositorio_mock, verificador_area_mock)

    with pytest.raises(AreaInvalidaError):
        await service.ejecutar(
            ActualizarUsuarioDTO(
                id_usuario="1",
                area_id="area-inexistente",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )

    repositorio_mock.guardar.assert_not_called()
