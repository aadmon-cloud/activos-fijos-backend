from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.services.obtener_pdf_auditoria import (
    ObtenerPdfAuditoriaService,
)
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria
from modules.auditorias.domain.errors import AuditoriaNoEncontradaError, PdfAuditoriaNoDisponibleError
from shared.application.file_storage.ports import ArchivoAlmacenado
from shared.domain.entities.audit import AuditPersona


def _auditoria(**overrides) -> Auditoria:
    valores = dict(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.NOTIFICADA,
        items=[],
        fecha_cierre=datetime.now(UTC),
        pdf_archivo_id="archivo-pdf-1",
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Auditoria(**valores)


async def test_obtener_pdf_falla_si_la_auditoria_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None
    service = ObtenerPdfAuditoriaService(repo, AsyncMock())

    with pytest.raises(AuditoriaNoEncontradaError):
        await service.ejecutar("aud-1")


async def test_obtener_pdf_falla_si_aun_no_se_genero():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria(pdf_archivo_id=None)
    service = ObtenerPdfAuditoriaService(repo, AsyncMock())

    with pytest.raises(PdfAuditoriaNoDisponibleError):
        await service.ejecutar("aud-1")


async def test_obtener_pdf_retorna_el_archivo():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    almacen_archivos = AsyncMock()
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )
    service = ObtenerPdfAuditoriaService(repo, almacen_archivos)

    archivo = await service.ejecutar("aud-1")

    assert archivo.contenido == b"%PDF-contenido"
    almacen_archivos.obtener.assert_called_once_with("archivo-pdf-1")
