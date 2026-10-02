from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.services.generar_comprobante_pdf import (
    GenerarComprobantePdfService,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import MovimientoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _salida():
    return Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        cliente_destino=None,
        ubicacion="A10-1",
        notas=None,
        remision="RM-001",
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "mov-1"})


def _entrada():
    return Movimiento.registrar_entrada(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        tipo_origen=None,
        origen_nombre=None,
        ubicacion="A10-1",
        notas=None,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "mov-2"})


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _salida()
    return mock


@pytest.fixture
def comprobante_port_mock():
    mock = AsyncMock()
    mock.generar_comprobante_salida.return_value = b"%PDF-1.4 contenido"
    return mock


@pytest.fixture
def service(movimiento_repository_mock, comprobante_port_mock):
    return GenerarComprobantePdfService(movimiento_repository_mock, comprobante_port_mock)


async def test_genera_el_comprobante(service, comprobante_port_mock):
    contenido = await service.ejecutar("mov-1")

    assert contenido == b"%PDF-1.4 contenido"
    comprobante_port_mock.generar_comprobante_salida.assert_called_once()


async def test_movimiento_no_encontrado_lanza_error(service, movimiento_repository_mock):
    movimiento_repository_mock.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar("no-existe")


async def test_movimiento_que_no_es_salida_lanza_error(service, movimiento_repository_mock):
    movimiento_repository_mock.obtener_por_id.return_value = _entrada()

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar("mov-2")
