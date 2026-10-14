from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarDevolucionDTO
from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.resolutor_nombres_port import NombresReferenciasMovimiento
from modules.movimientos.application.services.confirmar_devolucion_movimiento import (
    ConfirmarDevolucionMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import ResultadoChequeo as R
from modules.movimientos.domain.entities import TipoActa
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    NingunActivoChequeadoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto() -> ConfirmarDevolucionDTO:
    return ConfirmarDevolucionDTO(
        id_movimiento="m1", actor_id="u7", actor_nombre="Admin", actor_correo="admin@example.com"
    )


def _movimiento(fabrica, items=((I.EN_CURSO, R.ENCONTRADO),) * 2, **overrides):
    """Cada item es (estado, resultado del chequeo de ingreso); un resultado `None` es un activo sin chequear."""
    lista = [
        fabrica.item(
            activo_id=f"a{n}",
            responsable_original_id="u1",
            estado=estado,
            chequeo_ingreso=fabrica.chequeo(resultado) if resultado else None,
        )
        for n, (estado, resultado) in enumerate(items, start=1)
    ]
    return fabrica.movimiento(items=lista, estado=E.EN_CURSO, usuario_destino_id="u2", **overrides)


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
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMovimiento(
        usuarios={"u2": "Destino"}, correos={"u2": "destino@example.com"}
    )
    generador = AsyncMock()
    generador.generar_pdf.return_value = b"%PDF"
    almacen = AsyncMock()
    almacen.guardar.return_value = "archivo-9"
    notificador = AsyncMock()
    service = ConfirmarDevolucionMovimientoService(
        repo, activo_movimiento, EmisorActas(generador, almacen, resolutor), notificador
    )

    return service, repo, activo_movimiento, notificador


async def test_se_reciben_todos_los_chequeados_como_encontrados(fabrica):
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
    service, _, activo_movimiento, _ = _servicio(fabrica, _movimiento(fabrica, ((I.EN_CURSO, R.ENCONTRADO),)))

    await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_awaited_once_with("a1", "disponible", "u7", "Admin")
    activo_movimiento.cambiar_responsable.assert_awaited_once_with("a1", "u1", "u7", "Admin")


async def test_una_novedad_queda_en_el_movimiento_y_en_el_historial_del_activo(fabrica):
    movimiento = _movimiento(fabrica)
    con_novedad = replace(movimiento.items[1], chequeo_ingreso=fabrica.chequeo(R.CON_NOVEDAD, "Pantalla rayada"))
    movimiento = replace(movimiento, items=[movimiento.items[0], con_novedad])
    service, repo, activo_movimiento, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").novedad_devolucion is None
    assert guardado.item("a2").novedad_devolucion == "Pantalla rayada"
    activo_movimiento.registrar_nota.assert_awaited_once()
    argumentos = activo_movimiento.registrar_nota.await_args.args
    assert argumentos[0] == "a2"
    assert "Pantalla rayada" in argumentos[1]
    assert argumentos[2] == "m1"


async def test_lo_no_encontrado_o_sin_chequear_sigue_fuera_y_se_limpia_su_marca(fabrica):
    movimiento = _movimiento(
        fabrica, ((I.EN_CURSO, R.ENCONTRADO), (I.EN_CURSO, R.NO_ENCONTRADO), (I.DEVOLUCION_SOLICITADA, None))
    )
    service, repo, activo_movimiento, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.DEVUELTO, I.EN_CURSO, I.DEVOLUCION_SOLICITADA]
    assert guardado.item("a2").chequeo_ingreso is None
    assert guardado.estado == E.EN_CURSO
    assert guardado.fecha_devolucion_real is None
    assert activo_movimiento.cambiar_estado.await_count == 1


async def test_se_genera_el_acta_de_ingreso_con_lo_recibido_y_lo_que_sigue_fuera(fabrica):
    movimiento = _movimiento(fabrica, ((I.EN_CURSO, R.ENCONTRADO), (I.EN_CURSO, None)))
    movimiento = replace(movimiento, actas=[fabrica.acta()])
    service, repo, _, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    acta = repo.guardar.call_args.args[0].actas[-1]
    assert (acta.tipo, acta.numero) == (TipoActa.INGRESO, 1)
    assert [(l.activo_id, l.resultado) for l in acta.lineas] == [("a1", R.ENCONTRADO), ("a2", R.NO_ENCONTRADO)]
    assert acta.lineas[1].observacion
    assert acta.cerrada_por.correo == "admin@example.com"
    assert acta.aceptada_por is None
    # Las actas anteriores se conservan.
    assert len(repo.guardar.call_args.args[0].actas) == 2


async def test_el_segundo_ingreso_numera_su_acta_aparte(fabrica):
    movimiento = _movimiento(fabrica, ((I.EN_CURSO, R.ENCONTRADO),))
    previas = [fabrica.acta(id="s1"), fabrica.acta(id="i1", tipo=TipoActa.INGRESO)]
    movimiento = replace(movimiento, actas=previas)
    service, repo, _, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].actas[-1].numero == 2


async def test_sin_ningun_activo_encontrado_no_se_cierra_el_chequeo(fabrica):
    service, repo, activo_movimiento, _ = _servicio(
        fabrica, _movimiento(fabrica, ((I.EN_CURSO, R.NO_ENCONTRADO), (I.EN_CURSO, None)))
    )

    with pytest.raises(NingunActivoChequeadoError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()
    activo_movimiento.cambiar_estado.assert_not_called()


async def test_se_recibe_tambien_lo_que_ya_se_habia_pedido_de_vuelta(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica, ((I.DEVOLUCION_SOLICITADA, R.ENCONTRADO),)))

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].item("a1").estado == I.DEVUELTO


async def test_lo_ya_rechazado_o_devuelto_no_se_vuelve_a_recibir(fabrica):
    service, repo, _, _ = _servicio(
        fabrica, _movimiento(fabrica, ((I.EN_CURSO, R.ENCONTRADO), (I.RECHAZADO, None), (I.DEVUELTO, None)))
    )

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.DEVUELTO, I.RECHAZADO, I.DEVUELTO]


async def test_un_movimiento_sin_activos_fuera_no_admite_devolucion(fabrica):
    service, _, _, _ = _servicio(fabrica, _movimiento(fabrica, ((I.PENDIENTE_ADMIN, None),)))

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
        fabrica, _movimiento(fabrica, ((I.EN_CURSO, R.ENCONTRADO),)), cambiar_responsable=False
    )

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_any_await("a1", "prestado", "u7", "Admin")
    repo.guardar.assert_not_called()


async def test_si_no_se_puede_dejar_la_nota_la_devolucion_igual_se_confirma(fabrica):
    movimiento = _movimiento(fabrica, ((I.EN_CURSO, None),))
    movimiento = replace(
        movimiento, items=[replace(movimiento.items[0], chequeo_ingreso=fabrica.chequeo(R.CON_NOVEDAD, "Roto"))]
    )
    service, repo, activo_movimiento, _ = _servicio(fabrica, movimiento)
    activo_movimiento.registrar_nota.side_effect = RuntimeError("mongo caido")

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].item("a1").novedad_devolucion == "Roto"


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _, _ = _servicio(fabrica, _movimiento(fabrica))
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
