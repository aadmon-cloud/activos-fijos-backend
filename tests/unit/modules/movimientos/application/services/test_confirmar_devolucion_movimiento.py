from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.acciones_movimiento_dto import (
    ConfirmarDevolucionDTO,
    ReciboActivoDTO,
)
from modules.movimientos.application.services.confirmar_devolucion_movimiento import (
    ConfirmarDevolucionMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    MovimientoNoEncontradoError,
    ObservacionDeNovedadObligatoriaError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(recibos=None) -> ConfirmarDevolucionDTO:
    return ConfirmarDevolucionDTO(id_movimiento="m1", actor_id="u7", actor_nombre="Admin", recibos=recibos)


def _movimiento(fabrica, estados=(I.EN_CURSO, I.EN_CURSO), **overrides):
    items = [
        fabrica.item(activo_id=f"a{n}", responsable_original_id="u1", estado=estado)
        for n, estado in enumerate(estados, start=1)
    ]
    return fabrica.movimiento(items=items, estado=E.EN_CURSO, usuario_destino_id="u2", **overrides)


def _servicio(fabrica, movimiento, cambiar_estado=True, cambiar_responsable=True):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.cambiar_estado.return_value = cambiar_estado
    activo_movimiento.cambiar_responsable.return_value = cambiar_responsable
    activo_movimiento.obtener_resumenes.return_value = {
        item.activo_id: fabrica.resumen(id=item.activo_id) for item in movimiento.items
    }
    notificador = AsyncMock()

    return ConfirmarDevolucionMovimientoService(repo, activo_movimiento, notificador), repo, activo_movimiento, notificador


async def test_sin_recibos_se_reciben_todos_sin_novedad(fabrica):
    service, repo, activo_movimiento, notificador = _servicio(fabrica, _movimiento(fabrica))

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.DEVUELTO, I.DEVUELTO]
    assert all(i.novedad_devolucion is None for i in guardado.items)
    assert guardado.estado == E.DEVUELTO
    assert guardado.fecha_devolucion_real is not None
    assert guardado.item("a1").recibido_por.id_persona == "u7"
    activo_movimiento.registrar_nota.assert_not_called()
    notificador.notificar.assert_awaited_once()


async def test_el_activo_vuelve_a_disponible_y_a_su_responsable_original(fabrica):
    service, _, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica, (I.EN_CURSO,)))

    await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_awaited_once_with("a1", "disponible", "u7", "Admin")
    activo_movimiento.cambiar_responsable.assert_awaited_once_with("a1", "u1", "u7", "Admin")


async def test_una_novedad_queda_en_el_movimiento_y_en_el_historial_del_activo(fabrica):
    service, repo, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica))

    await service.ejecutar(
        _dto(
            [
                ReciboActivoDTO("a1"),
                ReciboActivoDTO("a2", con_novedad=True, observacion="  Pantalla rayada  "),
            ]
        )
    )

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").novedad_devolucion is None
    assert guardado.item("a2").novedad_devolucion == "Pantalla rayada"
    activo_movimiento.registrar_nota.assert_awaited_once()
    argumentos = activo_movimiento.registrar_nota.await_args.args
    assert argumentos[0] == "a2"
    assert "Pantalla rayada" in argumentos[1]
    assert argumentos[2] == "m1"


async def test_la_novedad_exige_describirla(fabrica):
    service, repo, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica, (I.EN_CURSO,)))

    with pytest.raises(ObservacionDeNovedadObligatoriaError):
        await service.ejecutar(_dto([ReciboActivoDTO("a1", con_novedad=True, observacion="  ")]))

    repo.guardar.assert_not_called()
    activo_movimiento.cambiar_estado.assert_not_called()


async def test_se_pueden_recibir_solo_algunos_y_el_movimiento_sigue_en_curso(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica))

    await service.ejecutar(_dto([ReciboActivoDTO("a1")]))

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.DEVUELTO
    assert guardado.item("a2").estado == I.EN_CURSO
    assert guardado.estado == E.EN_CURSO
    assert guardado.fecha_devolucion_real is None


async def test_se_recibe_tambien_lo_que_ya_se_habia_pedido_de_vuelta(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica, (I.DEVOLUCION_SOLICITADA,)))

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].item("a1").estado == I.DEVUELTO


async def test_lo_ya_rechazado_o_devuelto_no_se_vuelve_a_recibir(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica, (I.EN_CURSO, I.RECHAZADO, I.DEVUELTO)))

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.DEVUELTO, I.RECHAZADO, I.DEVUELTO]


async def test_un_activo_ajeno_al_movimiento_se_rechaza(fabrica):
    service, _, _, _ = _servicio(fabrica, _movimiento(fabrica))

    with pytest.raises(ActivoNoPerteneceAlMovimientoError):
        await service.ejecutar(_dto([ReciboActivoDTO("zzz")]))


async def test_un_movimiento_sin_activos_fuera_no_admite_devolucion(fabrica):
    service, _, _, _ = _servicio(fabrica, _movimiento(fabrica, (I.PENDIENTE_ADMIN,)))

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())


async def test_si_falla_el_segundo_activo_se_deshace_el_primero(fabrica):
    service, repo, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica))
    activo_movimiento.cambiar_estado.side_effect = [True, False, True]

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()
    # a1 vuelve a quedar prestado y a cargo de quien lo tenia.
    activo_movimiento.cambiar_responsable.assert_any_await("a1", "u2", "u7", "Admin")
    activo_movimiento.cambiar_estado.assert_any_await("a1", "prestado", "u7", "Admin")


async def test_si_falla_el_responsable_se_deshace_el_estado(fabrica):
    service, repo, activo_movimiento, _ = _servicio(
        fabrica, _movimiento(fabrica, (I.EN_CURSO,)), cambiar_responsable=False
    )

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_any_await("a1", "prestado", "u7", "Admin")
    repo.guardar.assert_not_called()


async def test_si_no_se_puede_dejar_la_nota_la_devolucion_igual_se_confirma(fabrica):
    service, repo, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica, (I.EN_CURSO,)))
    activo_movimiento.registrar_nota.side_effect = RuntimeError("mongo caido")

    await service.ejecutar(_dto([ReciboActivoDTO("a1", con_novedad=True, observacion="Roto")]))

    assert repo.guardar.call_args.args[0].item("a1").novedad_devolucion == "Roto"


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica))
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
