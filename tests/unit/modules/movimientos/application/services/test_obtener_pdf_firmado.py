from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.services.obtener_pdf_firmado import (
    ObtenerPdfFirmadoService,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    PdfFirmadoNoEncontradoError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _salida_con_pdf():
    movimiento = Movimiento.registrar_salida(
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
    return movimiento.adjuntar_pdf_firmado(
        "pdfs/salidas/mov-1_firmado.pdf", "firmado.pdf", _audit_persona()
    )


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _salida_con_pdf()
    return mock


@pytest.fixture
def storage_repository_mock():
    mock = AsyncMock()
    mock.leer.return_value = b"contenido-pdf"
    return mock


@pytest.fixture
def service(movimiento_repository_mock, storage_repository_mock):
    return ObtenerPdfFirmadoService(movimiento_repository_mock, storage_repository_mock)


async def test_obtiene_el_pdf_firmado(service, storage_repository_mock):
    contenido, nombre = await service.ejecutar("mov-1")

    assert contenido == b"contenido-pdf"
    assert nombre == "firmado.pdf"
    storage_repository_mock.leer.assert_called_once_with("pdfs/salidas/mov-1_firmado.pdf")


async def test_movimiento_no_encontrado_lanza_error(service, movimiento_repository_mock):
    movimiento_repository_mock.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar("no-existe")


async def test_sin_pdf_firmado_lanza_error(service, movimiento_repository_mock):
    movimiento_repository_mock.obtener_por_id.return_value = Movimiento.registrar_salida(
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

    with pytest.raises(PdfFirmadoNoEncontradoError):
        await service.ejecutar("mov-1")
