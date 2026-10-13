from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.application.services.reenviar_notificacion_auditoria import (
    ReenviarNotificacionAuditoriaService,
)
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria
from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    AuditoriaNoModificableError,
    PdfAuditoriaNoDisponibleError,
)
from shared.application.file_storage.ports import ArchivoAlmacenado
from shared.domain.entities.audit import AuditPersona


def _auditoria(**overrides) -> Auditoria:
    valores = dict(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.ERROR_NOTIFICACION,
        items=[],
        fecha_cierre=datetime.now(UTC),
        pdf_archivo_id="archivo-pdf-1",
        detalle_error_notificacion="smtp caido",
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Auditoria(**valores)


def _usuario() -> UsuarioAuditado:
    return UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="camilo@x.com", activo=True
    )


async def test_reenviar_falla_si_la_auditoria_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None
    service = ReenviarNotificacionAuditoriaService(repo, AsyncMock(), AsyncMock(), AsyncMock())

    with pytest.raises(AuditoriaNoEncontradaError):
        await service.ejecutar("aud-1")


async def test_reenviar_falla_si_la_auditoria_sigue_en_progreso():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria(estado=EstadoAuditoria.EN_PROGRESO)
    service = ReenviarNotificacionAuditoriaService(repo, AsyncMock(), AsyncMock(), AsyncMock())

    with pytest.raises(AuditoriaNoModificableError):
        await service.ejecutar("aud-1")


async def test_reenviar_falla_si_no_hay_pdf_generado():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria(pdf_archivo_id=None)
    service = ReenviarNotificacionAuditoriaService(repo, AsyncMock(), AsyncMock(), AsyncMock())

    with pytest.raises(PdfAuditoriaNoDisponibleError):
        await service.ejecutar("aud-1")


async def test_reenviar_exitoso_queda_notificada_sin_regenerar_el_pdf():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = _usuario()
    almacen_archivos = AsyncMock()
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )
    notificador = AsyncMock()
    service = ReenviarNotificacionAuditoriaService(repo, usuario_auditado, almacen_archivos, notificador)

    resultado = await service.ejecutar("aud-1")

    assert resultado.estado == EstadoAuditoria.NOTIFICADA
    notificador.enviar.assert_called_once()
    almacen_archivos.guardar.assert_not_called()


async def test_reenviar_fallido_mantiene_error_notificacion_con_el_nuevo_detalle():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = _usuario()
    almacen_archivos = AsyncMock()
    almacen_archivos.obtener.return_value = ArchivoAlmacenado(
        nombre="auditoria.pdf", tipo_mime="application/pdf", contenido=b"%PDF-contenido"
    )
    notificador = AsyncMock()
    notificador.enviar.side_effect = RuntimeError("smtp sigue caido")
    service = ReenviarNotificacionAuditoriaService(repo, usuario_auditado, almacen_archivos, notificador)

    resultado = await service.ejecutar("aud-1")

    assert resultado.estado == EstadoAuditoria.ERROR_NOTIFICACION
    assert resultado.detalle_error_notificacion == "smtp sigue caido"
