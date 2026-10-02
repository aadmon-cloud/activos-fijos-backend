from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.application.services.listar_movimientos_pendientes import (
    ListarMovimientosPendientesService,
)


@pytest.fixture
def movimiento_pendiente_repository_mock():
    mock = AsyncMock()
    mock.listar.return_value = ([], 0)
    return mock


@pytest.fixture
def service(movimiento_pendiente_repository_mock):
    return ListarMovimientosPendientesService(movimiento_pendiente_repository_mock)


async def test_super_admin_ve_todas_sin_filtro_de_dueno(
    service, movimiento_pendiente_repository_mock
):
    entrada = ListarMovimientosPendientesInput()

    await service.ejecutar(entrada, usuario_actual_id="admin-1", es_super_admin=True)

    filtro_usado = movimiento_pendiente_repository_mock.listar.call_args.args[0]
    assert filtro_usado.creado_por_id is None


async def test_no_super_admin_solo_ve_las_propias(service, movimiento_pendiente_repository_mock):
    entrada = ListarMovimientosPendientesInput()

    await service.ejecutar(entrada, usuario_actual_id="usuario-1", es_super_admin=False)

    filtro_usado = movimiento_pendiente_repository_mock.listar.call_args.args[0]
    assert filtro_usado.creado_por_id == "usuario-1"


async def test_ignora_cualquier_creado_por_id_que_venga_en_el_input(
    service, movimiento_pendiente_repository_mock
):
    """El filtro de dueño lo decide el servicio según el rol, no lo que
    traiga el DTO — evita que un no-super_admin vea propuestas de otro
    usuario manipulando el request."""
    entrada = ListarMovimientosPendientesInput(creado_por_id="otro-usuario")

    await service.ejecutar(entrada, usuario_actual_id="usuario-1", es_super_admin=False)

    filtro_usado = movimiento_pendiente_repository_mock.listar.call_args.args[0]
    assert filtro_usado.creado_por_id == "usuario-1"
