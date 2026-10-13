from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.dto.iniciar_auditoria_dto import IniciarAuditoriaDTO
from modules.auditorias.application.ports.activos_asignados_port import ActivoAsignado
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.application.services.iniciar_auditoria import IniciarAuditoriaService
from modules.auditorias.domain.entities import EstadoAuditoria
from modules.auditorias.domain.errors import UsuarioNoEncontradoParaAuditoriaError

_DTO = IniciarAuditoriaDTO(usuario_auditado_id="u1", auditor_id="admin-1", auditor_nombre="Admin")


def _usuario() -> UsuarioAuditado:
    return UsuarioAuditado(
        id="u1", nombre_completo="Camilo Perez", identificacion="123", email="c@x.com", activo=True
    )


async def test_iniciar_auditoria_falla_si_el_usuario_no_existe():
    repo = AsyncMock()
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = None
    activos_asignados = AsyncMock()
    service = IniciarAuditoriaService(repo, usuario_auditado, activos_asignados)

    with pytest.raises(UsuarioNoEncontradoParaAuditoriaError):
        await service.ejecutar(_DTO)

    repo.guardar.assert_not_called()


async def test_iniciar_auditoria_toma_el_snapshot_de_activos_asignados():
    repo = AsyncMock()
    repo.guardar.side_effect = lambda auditoria: replace(auditoria, id="aud-1")
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = _usuario()
    activos_asignados = AsyncMock()
    activos_asignados.listar_por_responsable.return_value = [
        ActivoAsignado(
            id="a1",
            nombre="Laptop",
            numero_inventario="INV-1",
            tipo="activo_fijo",
            descripcion="Dell",
            serie="SN1",
            estado_ciclo_vida="disponible",
        )
    ]
    service = IniciarAuditoriaService(repo, usuario_auditado, activos_asignados)

    resultado = await service.ejecutar(_DTO)

    assert resultado.total == 1
    assert resultado.pendientes == 1
    auditoria_guardada = repo.guardar.call_args.args[0]
    assert auditoria_guardada.estado == EstadoAuditoria.EN_PROGRESO
    assert auditoria_guardada.items[0].activo_id == "a1"
    assert auditoria_guardada.items[0].resultado is None
    assert auditoria_guardada.creado_por.id_persona == "admin-1"


async def test_iniciar_auditoria_permite_un_snapshot_vacio():
    repo = AsyncMock()
    usuario_auditado = AsyncMock()
    usuario_auditado.obtener.return_value = _usuario()
    activos_asignados = AsyncMock()
    activos_asignados.listar_por_responsable.return_value = []
    service = IniciarAuditoriaService(repo, usuario_auditado, activos_asignados)

    await service.ejecutar(_DTO)

    auditoria_guardada = repo.guardar.call_args.args[0]
    assert auditoria_guardada.items == []
