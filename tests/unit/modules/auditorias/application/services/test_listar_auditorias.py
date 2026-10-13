from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.auditorias.application.dto.listar_auditorias_dto import ListarAuditoriasDTO
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.application.services.listar_auditorias import ListarAuditoriasService
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria
from shared.domain.entities.audit import AuditPersona


def _auditoria(id_: str, usuario_auditado_id: str) -> Auditoria:
    return Auditoria(
        id=id_,
        usuario_auditado_id=usuario_auditado_id,
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


async def test_listar_retorna_meta_y_resuelve_nombres():
    repo = AsyncMock()
    repo.listar.return_value = [_auditoria("aud-1", "u1")]
    repo.contar.return_value = 1
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="c@x.com", activo=True
    )
    service = ListarAuditoriasService(repo, usuario_auditado)

    listado = await service.ejecutar(ListarAuditoriasDTO())

    assert listado.total == 1
    assert listado.items[0].usuario_nombre == "Camilo Perez"


async def test_listar_no_consulta_el_mismo_usuario_dos_veces():
    repo = AsyncMock()
    repo.listar.return_value = [_auditoria("aud-1", "u1"), _auditoria("aud-2", "u1")]
    repo.contar.return_value = 2
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="c@x.com", activo=True
    )
    service = ListarAuditoriasService(repo, usuario_auditado)

    await service.ejecutar(ListarAuditoriasDTO())

    usuario_auditado.obtener.assert_called_once_with("u1")


async def test_listar_respeta_el_limite_maximo():
    repo = AsyncMock()
    repo.listar.return_value = []
    repo.contar.return_value = 0
    service = ListarAuditoriasService(repo, AsyncMock())

    listado = await service.ejecutar(ListarAuditoriasDTO(limit=5000))

    assert listado.limit == 1000
