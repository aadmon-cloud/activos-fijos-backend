from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.application.services.obtener_auditoria import ObtenerAuditoriaService
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria
from modules.auditorias.domain.errors import AuditoriaNoEncontradaError
from shared.domain.entities.audit import AuditPersona


def _auditoria() -> Auditoria:
    return Auditoria(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


async def test_obtener_falla_si_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None
    service = ObtenerAuditoriaService(repo, AsyncMock())

    with pytest.raises(AuditoriaNoEncontradaError):
        await service.ejecutar("aud-1")


async def test_obtener_incluye_los_datos_del_usuario_auditado():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="c@x.com", activo=True
    )
    service = ObtenerAuditoriaService(repo, usuario_auditado)

    resultado = await service.ejecutar("aud-1")

    assert resultado.usuario_nombre == "Camilo Perez"
    assert resultado.usuario_identificacion == "123"
    assert resultado.usuario_email == "c@x.com"


async def test_obtener_no_falla_si_el_usuario_ya_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = None
    service = ObtenerAuditoriaService(repo, usuario_auditado)

    resultado = await service.ejecutar("aud-1")

    assert resultado.usuario_nombre is None
