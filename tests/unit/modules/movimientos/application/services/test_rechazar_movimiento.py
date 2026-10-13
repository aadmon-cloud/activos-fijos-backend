from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.rechazar_movimiento_dto import RechazarMovimientoDTO
from modules.movimientos.application.services.rechazar_movimiento import RechazarMovimientoService
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import EtapaRechazo, TipoMovimiento
from modules.movimientos.domain.errors import (
    MotivoRechazoObligatorioError,
    MovimientoNoEncontradoError,
    PermisoAprobacionError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(actor_id="u1", rol="empleado", motivo="No se puede", activo_ids=None) -> RechazarMovimientoDTO:
    return RechazarMovimientoDTO(
        id_movimiento="m1",
        motivo_rechazo=motivo,
        actor_id=actor_id,
        actor_nombre="Actor",
        actor_rol=rol,
        activo_ids=activo_ids,
    )


def _servicio(fabrica, movimiento):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {
        item.activo_id: fabrica.resumen(id=item.activo_id, responsable_id=item.responsable_original_id)
        for item in movimiento.items
    }
    notificador = AsyncMock()

    return RechazarMovimientoService(repo, activo_movimiento, notificador), repo, notificador


async def test_el_responsable_rechaza_su_activo_con_motivo(fabrica):
    movimiento = fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1"),
            fabrica.item(activo_id="a2", responsable_original_id="u3"),
        ]
    )
    service, repo, notificador = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto("u1", motivo="Lo necesito yo"))

    guardado = repo.guardar.call_args.args[0]
    rechazado = guardado.item("a1")
    assert rechazado.estado == I.RECHAZADO
    assert rechazado.motivo_rechazo == "Lo necesito yo"
    assert rechazado.etapa_rechazo == EtapaRechazo.RESPONSABLE
    assert rechazado.rechazado_por.id_persona == "u1"
    assert guardado.item("a2").estado == I.PENDIENTE_RESPONSABLE
    assert guardado.estado == E.SOLICITADO
    notificador.notificar.assert_awaited_once()


async def test_si_se_rechazan_todos_el_movimiento_queda_rechazado(fabrica):
    service, repo, _ = _servicio(fabrica, fabrica.movimiento())

    await service.ejecutar(_dto("u1"))

    assert repo.guardar.call_args.args[0].estado == E.RECHAZADO


async def test_administracion_rechaza_lo_que_espera_su_confirmacion(fabrica):
    movimiento = fabrica.movimiento(
        estado=E.APROBADO_RESPONSABLE, items=[fabrica.item(estado=I.PENDIENTE_ADMIN)]
    )
    service, repo, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto("u7", rol="administrador_general"))

    rechazado = repo.guardar.call_args.args[0].item("a1")
    assert rechazado.estado == I.RECHAZADO
    assert rechazado.etapa_rechazo == EtapaRechazo.ADMINISTRACION


async def test_el_motivo_es_obligatorio(fabrica):
    service, repo, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(MotivoRechazoObligatorioError):
        await service.ejecutar(_dto(motivo="   "))

    repo.guardar.assert_not_called()


async def test_quien_no_decide_ningun_activo_no_puede_rechazar(fabrica):
    movimiento = fabrica.movimiento(creado_por=fabrica.audit("u9", "Otro"))
    service, repo, _ = _servicio(fabrica, movimiento)

    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u9"))

    repo.guardar.assert_not_called()


async def test_quien_no_ve_el_movimiento_recibe_no_encontrado(fabrica):
    service, _, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto("u9"))


async def test_un_movimiento_que_no_espera_decision_no_se_rechaza(fabrica):
    movimiento = fabrica.movimiento(items=[fabrica.item(estado=I.EN_CURSO)], estado=E.EN_CURSO)
    service, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto("u1"))


async def test_una_baja_aprobada_ya_no_se_rechaza(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA,
        usuario_destino_id=None,
        estado=E.APROBADO,
        items=[fabrica.item(estado=I.PENDIENTE_ADMIN)],
    )
    service, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto("u7", rol="administrador_general"))


async def test_se_rechaza_una_baja_solicitada(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA, usuario_destino_id=None, items=[fabrica.item(estado=I.PENDIENTE_ADMIN)]
    )
    service, repo, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto("u7", rol="administrador_general"))

    assert repo.guardar.call_args.args[0].estado == E.RECHAZADO
