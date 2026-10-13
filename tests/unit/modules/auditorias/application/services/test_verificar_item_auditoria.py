from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.auditorias.application.dto.verificar_item_auditoria_dto import (
    VerificarItemAuditoriaDTO,
)
from modules.auditorias.application.services.verificar_item_auditoria import (
    VerificarItemAuditoriaService,
)
from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    AuditoriaNoModificableError,
    ItemAuditoriaNoEncontradoError,
    ObservacionObligatoriaError,
)
from shared.domain.entities.audit import AuditPersona


def _item(**overrides) -> ItemAuditoria:
    valores = dict(
        activo_id="a1",
        nombre="Laptop",
        numero_inventario="INV-1",
        tipo="activo_fijo",
        descripcion=None,
        serie=None,
        estado_ciclo_vida_al_inicio="disponible",
        resultado=None,
        observacion=None,
        verificado_en=None,
    )
    valores.update(overrides)
    return ItemAuditoria(**valores)


def _auditoria(**overrides) -> Auditoria:
    valores = dict(
        id="aud-1",
        usuario_auditado_id="u1",
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[_item()],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Auditoria(**valores)


async def test_verificar_item_falla_si_la_auditoria_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None
    service = VerificarItemAuditoriaService(repo)

    with pytest.raises(AuditoriaNoEncontradaError):
        await service.ejecutar(
            VerificarItemAuditoriaDTO(
                id_auditoria="aud-1", activo_id="a1", resultado=ResultadoVerificacion.ENCONTRADO
            )
        )


async def test_verificar_item_falla_si_la_auditoria_ya_fue_cerrada():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria(estado=EstadoAuditoria.FINALIZADA)
    service = VerificarItemAuditoriaService(repo)

    with pytest.raises(AuditoriaNoModificableError):
        await service.ejecutar(
            VerificarItemAuditoriaDTO(
                id_auditoria="aud-1", activo_id="a1", resultado=ResultadoVerificacion.ENCONTRADO
            )
        )


async def test_verificar_item_falla_si_el_activo_no_esta_en_el_snapshot():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    service = VerificarItemAuditoriaService(repo)

    with pytest.raises(ItemAuditoriaNoEncontradoError):
        await service.ejecutar(
            VerificarItemAuditoriaDTO(
                id_auditoria="aud-1", activo_id="no-existe", resultado=ResultadoVerificacion.ENCONTRADO
            )
        )


async def test_verificar_item_con_novedad_sin_observacion_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    service = VerificarItemAuditoriaService(repo)

    with pytest.raises(ObservacionObligatoriaError):
        await service.ejecutar(
            VerificarItemAuditoriaDTO(
                id_auditoria="aud-1",
                activo_id="a1",
                resultado=ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD,
            )
        )


async def test_verificar_item_con_novedad_y_observacion_en_blanco_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    service = VerificarItemAuditoriaService(repo)

    with pytest.raises(ObservacionObligatoriaError):
        await service.ejecutar(
            VerificarItemAuditoriaDTO(
                id_auditoria="aud-1",
                activo_id="a1",
                resultado=ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD,
                observacion="   ",
            )
        )


async def test_verificar_item_encontrado_actualiza_el_resultado_y_la_fecha():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1", activo_id="a1", resultado=ResultadoVerificacion.ENCONTRADO
        )
    )

    assert resultado.items[0].resultado == ResultadoVerificacion.ENCONTRADO
    assert resultado.items[0].verificado_en is not None
    assert resultado.pendientes == 0


async def test_verificar_item_con_novedad_y_observacion_queda_registrado():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1",
            activo_id="a1",
            resultado=ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD,
            observacion="Danio en pantalla",
        )
    )

    assert resultado.items[0].resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD
    assert resultado.items[0].observacion == "Danio en pantalla"
    assert resultado.encontrados_con_novedad == 1


async def test_verificar_item_no_afecta_otros_items_del_snapshot():
    repo = AsyncMock()
    auditoria = _auditoria(items=[_item(), _item(activo_id="a2")])
    repo.obtener_por_id.return_value = auditoria
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1", activo_id="a1", resultado=ResultadoVerificacion.ENCONTRADO
        )
    )

    item_sin_tocar = next(i for i in resultado.items if i.activo_id == "a2")
    assert item_sin_tocar.resultado is None


async def test_verificar_item_permite_corregir_un_resultado_ya_registrado():
    repo = AsyncMock()
    item_ya_verificado = _item(
        resultado=ResultadoVerificacion.ENCONTRADO, verificado_en=datetime.now(UTC)
    )
    repo.obtener_por_id.return_value = _auditoria(items=[item_ya_verificado])
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1", activo_id="a1", resultado=ResultadoVerificacion.NO_ENCONTRADO
        )
    )

    assert resultado.items[0].resultado == ResultadoVerificacion.NO_ENCONTRADO


async def test_la_observacion_se_guarda_sin_espacios_sobrantes():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1",
            activo_id="a1",
            resultado=ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD,
            observacion="  Pantalla rayada  ",
        )
    )

    assert resultado.items[0].observacion == "Pantalla rayada"


async def test_una_observacion_en_blanco_en_un_encontrado_no_se_guarda():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = _auditoria()
    repo.guardar.side_effect = lambda auditoria: auditoria
    service = VerificarItemAuditoriaService(repo)

    resultado = await service.ejecutar(
        VerificarItemAuditoriaDTO(
            id_auditoria="aud-1",
            activo_id="a1",
            resultado=ResultadoVerificacion.ENCONTRADO,
            observacion="   ",
        )
    )

    assert resultado.items[0].observacion is None
