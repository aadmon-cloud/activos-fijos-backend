from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _movimiento():
    return Movimiento.registrar_entrada(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=10,
        motivo=None,
        tipo_origen=None,
        origen_nombre=None,
        ubicacion="A10-1",
        notas=None,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "mov-1"})


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.listar.return_value = ([_movimiento()], 1)
    return mock


@pytest.fixture
def service(movimiento_repository_mock):
    return ListarMovimientosService(movimiento_repository_mock)


async def test_devuelve_respuesta_paginada(service, movimiento_repository_mock):
    entrada = ListarMovimientosInput(pagina=1, limite=20)

    resultado = await service.ejecutar(entrada)

    movimiento_repository_mock.listar.assert_called_once_with(entrada)
    assert resultado.total_elementos == 1
    assert resultado.pagina_actual == 1
    assert resultado.elementos_por_pagina == 20
    assert len(resultado.resultado) == 1
