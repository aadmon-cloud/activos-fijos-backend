from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.services.subir_pdf_firmado import SubirPdfFirmadoService
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import ArchivoNoEsPdfError, MovimientoNoEncontradoError
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


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _salida()
    mock.actualizar.side_effect = lambda movimiento, uow=None: movimiento
    return mock


@pytest.fixture
def storage_repository_mock():
    mock = AsyncMock()
    mock.guardar.return_value = "pdfs/salidas/mov-1_firmado.pdf"
    return mock


@pytest.fixture
def service(movimiento_repository_mock, storage_repository_mock):
    return SubirPdfFirmadoService(movimiento_repository_mock, storage_repository_mock)


async def test_sube_el_pdf_y_actualiza_el_movimiento(
    service, storage_repository_mock, movimiento_repository_mock
):
    movimiento = await service.ejecutar("mov-1", "firmado.pdf", b"contenido", _audit_persona())

    storage_repository_mock.guardar.assert_called_once_with(
        "pdfs/salidas", "mov-1_firmado.pdf", b"contenido"
    )
    assert movimiento.pdf_firmado == "pdfs/salidas/mov-1_firmado.pdf"
    assert movimiento.pdf_nombre == "firmado.pdf"
    movimiento_repository_mock.actualizar.assert_called_once()


async def test_movimiento_no_encontrado_lanza_error(service, movimiento_repository_mock):
    movimiento_repository_mock.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar("no-existe", "firmado.pdf", b"contenido", _audit_persona())


async def test_archivo_no_es_pdf_lanza_error(service):
    with pytest.raises(ArchivoNoEsPdfError):
        await service.ejecutar("mov-1", "firmado.docx", b"contenido", _audit_persona())
