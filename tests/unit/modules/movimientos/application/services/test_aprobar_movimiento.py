from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.aprobar_movimiento_dto import AprobarMovimientoDTO
from modules.movimientos.application.services.aprobar_movimiento import AprobarMovimientoService
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import TipoMovimiento
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    MovimientoNoEncontradoError,
    PermisoAprobacionError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(actor_id="u1", rol="empleado", activo_ids=None) -> AprobarMovimientoDTO:
    return AprobarMovimientoDTO(
        id_movimiento="m1", actor_id=actor_id, actor_nombre="Actor", actor_rol=rol, activo_ids=activo_ids
    )


def _servicio(fabrica, movimiento, responsables=None):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    responsables = responsables or {item.activo_id: item.responsable_original_id for item in movimiento.items}
    activo_movimiento.obtener_resumenes.return_value = {
        activo_id: fabrica.resumen(id=activo_id, responsable_id=responsable)
        for activo_id, responsable in responsables.items()
    }
    notificador = AsyncMock()

    return AprobarMovimientoService(repo, activo_movimiento, notificador), repo, notificador


def _dos_responsables(fabrica):
    return fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1"),
            fabrica.item(activo_id="a2", responsable_original_id="u3"),
        ]
    )


async def test_el_responsable_aprueba_su_activo_y_el_movimiento_sigue_esperando_a_los_demas(fabrica):
    service, repo, _ = _servicio(fabrica, _dos_responsables(fabrica))

    await service.ejecutar(_dto("u1"))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.PENDIENTE_ADMIN
    assert guardado.item("a1").aprobado_por_responsable.id_persona == "u1"
    assert guardado.item("a2").estado == I.PENDIENTE_RESPONSABLE
    assert guardado.estado == E.SOLICITADO


async def test_cuando_el_ultimo_responsable_aprueba_pasa_a_administracion(fabrica):
    service, repo, notificador = _servicio(fabrica, _dos_responsables(fabrica))

    await service.ejecutar(_dto("u1"))
    movimiento_a_medias = repo.guardar.call_args.args[0]
    service, repo, notificador = _servicio(fabrica, movimiento_a_medias)
    await service.ejecutar(_dto("u3"))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.estado == E.APROBADO_RESPONSABLE
    assert notificador.notificar.await_args.kwargs["destinatarios"] == [
        "rol:administrador_general",
        "usuario:u2",
    ]


async def test_se_puede_aprobar_solo_una_parte_de_lo_que_se_decide(fabrica):
    movimiento = fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1"),
            fabrica.item(activo_id="a2", responsable_original_id="u1"),
        ]
    )
    service, repo, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto("u1", activo_ids=["a2"]))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.PENDIENTE_RESPONSABLE
    assert guardado.item("a2").estado == I.PENDIENTE_ADMIN


async def test_no_se_puede_aprobar_un_activo_que_decide_otro_responsable(fabrica):
    service, repo, _ = _servicio(fabrica, _dos_responsables(fabrica))

    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u1", activo_ids=["a1", "a2"]))

    repo.guardar.assert_not_called()


async def test_quien_no_es_responsable_de_ninguno_no_puede_aprobar(fabrica):
    movimiento = fabrica.movimiento(creado_por=fabrica.audit("u9", "Otro"))
    service, repo, _ = _servicio(fabrica, movimiento)

    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u9"))

    repo.guardar.assert_not_called()


async def test_un_activo_que_no_es_del_movimiento_se_rechaza(fabrica):
    service, _, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(ActivoNoPerteneceAlMovimientoError):
        await service.ejecutar(_dto("u1", activo_ids=["zzz"]))


async def test_el_administrador_no_aprueba_por_el_responsable(fabrica):
    service, _, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(PermisoAprobacionError):
        await service.ejecutar(_dto("u7", rol="administrador_general"))


async def test_quien_no_ve_el_movimiento_recibe_no_encontrado(fabrica):
    service, _, _ = _servicio(fabrica, fabrica.movimiento())

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto("u9"))


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _ = _servicio(fabrica, fabrica.movimiento())
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())


async def test_un_movimiento_que_no_espera_aprobacion_se_rechaza(fabrica):
    movimiento = fabrica.movimiento(items=[fabrica.item(estado=I.EN_CURSO)], estado=E.EN_CURSO)
    service, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto("u1"))


async def test_administracion_aprueba_la_baja(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA,
        usuario_destino_id=None,
        items=[fabrica.item(estado=I.PENDIENTE_ADMIN)],
    )
    service, repo, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto("u7", rol="administrador_general"))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.estado == E.APROBADO
    assert guardado.aprobado_por_admin.id_persona == "u7"


async def test_una_baja_ya_aprobada_no_se_aprueba_de_nuevo(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA,
        usuario_destino_id=None,
        estado=E.APROBADO,
        items=[fabrica.item(estado=I.PENDIENTE_ADMIN)],
    )
    service, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto("u7", rol="administrador_general"))
