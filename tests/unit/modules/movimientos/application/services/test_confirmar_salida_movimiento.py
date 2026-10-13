from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarSalidaDTO
from modules.movimientos.application.ports.resolutor_nombres_port import NombresReferenciasMovimiento
from modules.movimientos.application.services.confirmar_salida_movimiento import (
    ConfirmarSalidaMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento as I,
)
from modules.movimientos.domain.entities import (
    EstadoMovimiento as E,
)
from modules.movimientos.domain.entities import EtapaRechazo, TipoMovimiento
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    MovimientoNoEncontradoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(activo_ids=None, motivo=None) -> ConfirmarSalidaDTO:
    return ConfirmarSalidaDTO(
        id_movimiento="m1", actor_id="u7", actor_nombre="Admin", activo_ids=activo_ids, motivo_no_incluidos=motivo
    )


def _movimiento(fabrica, n=3, **overrides):
    items = [
        fabrica.item(activo_id=f"a{k}", responsable_original_id="u1", estado=I.PENDIENTE_ADMIN)
        for k in range(1, n + 1)
    ]
    return fabrica.movimiento(items=items, estado=E.APROBADO_RESPONSABLE, usuario_destino_id="u2", **overrides)


def _servicio(fabrica, movimiento, cambiar_estado=True, cambiar_responsable=True):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.cambiar_estado.return_value = cambiar_estado
    activo_movimiento.cambiar_responsable.return_value = cambiar_responsable
    activo_movimiento.obtener_resumenes.return_value = {
        item.activo_id: fabrica.resumen(id=item.activo_id, nombre=f"Activo {item.activo_id}")
        for item in movimiento.items
    }
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMovimiento(usuarios={"u2": "Destino"})
    generador = AsyncMock()
    generador.generar_pdf.return_value = b"%PDF"
    almacen = AsyncMock()
    almacen.guardar.return_value = "archivo-1"
    notificador = AsyncMock()
    service = ConfirmarSalidaMovimientoService(
        repo, activo_movimiento, resolutor, generador, almacen, notificador
    )

    return service, repo, activo_movimiento, generador, notificador


async def test_sin_seleccion_salen_todos_los_activos_pendientes(fabrica):
    service, repo, activo_movimiento, _, notificador = _servicio(fabrica, _movimiento(fabrica))

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.EN_CURSO] * 3
    assert guardado.estado == E.EN_CURSO
    assert guardado.aprobado_por_admin.id_persona == "u7"
    assert guardado.fecha_entrega_real is not None
    assert activo_movimiento.cambiar_estado.await_count == 3
    activo_movimiento.cambiar_responsable.assert_any_await("a1", "u2", "u7", "Admin")
    notificador.notificar.assert_awaited_once()


async def test_el_activo_pasa_a_prestado_a_cargo_del_destinatario(fabrica):
    service, _, activo_movimiento, _, _ = _servicio(fabrica, _movimiento(fabrica, n=1))

    await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_awaited_once_with("a1", "prestado", "u7", "Admin")
    activo_movimiento.cambiar_responsable.assert_awaited_once_with("a1", "u2", "u7", "Admin")


async def test_administracion_elige_solo_algunos_y_el_resto_queda_rechazado(fabrica):
    service, repo, activo_movimiento, _, _ = _servicio(fabrica, _movimiento(fabrica, n=4))

    await service.ejecutar(_dto(activo_ids=["a1", "a3"], motivo="Solo hay dos disponibles"))

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.EN_CURSO, I.RECHAZADO, I.EN_CURSO, I.RECHAZADO]
    rechazado = guardado.item("a2")
    assert rechazado.etapa_rechazo == EtapaRechazo.ADMINISTRACION
    assert rechazado.motivo_rechazo == "Solo hay dos disponibles"
    assert rechazado.rechazado_por.id_persona == "u7"
    assert activo_movimiento.cambiar_estado.await_count == 2


async def test_los_no_elegidos_llevan_un_motivo_por_defecto(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, _movimiento(fabrica, n=2))

    await service.ejecutar(_dto(activo_ids=["a1"]))

    assert repo.guardar.call_args.args[0].item("a2").motivo_rechazo


async def test_solo_se_confirman_los_activos_que_esperan_a_administracion(fabrica):
    movimiento = _movimiento(fabrica, n=2)
    items = [movimiento.items[0], fabrica.item(activo_id="a2", estado=I.RECHAZADO)]
    movimiento = fabrica.movimiento(items=items, estado=E.APROBADO_RESPONSABLE)
    service, repo, _, _, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.EN_CURSO
    assert guardado.item("a2").estado == I.RECHAZADO


async def test_un_activo_que_no_espera_a_administracion_no_se_puede_elegir(fabrica):
    movimiento = fabrica.movimiento(
        items=[fabrica.item(activo_id="a1", estado=I.PENDIENTE_ADMIN), fabrica.item(activo_id="a2", estado=I.PENDIENTE_RESPONSABLE)],
        estado=E.SOLICITADO,
    )
    service, _, _, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto(activo_ids=["a1", "a2"]))


async def test_un_activo_ajeno_al_movimiento_se_rechaza(fabrica):
    service, _, _, _, _ = _servicio(fabrica, _movimiento(fabrica))

    with pytest.raises(ActivoNoPerteneceAlMovimientoError):
        await service.ejecutar(_dto(activo_ids=["zzz"]))


async def test_la_salida_a_evento_genera_el_comprobante_con_los_activos_que_salen(fabrica):
    movimiento = _movimiento(fabrica, n=2, tipo=TipoMovimiento.SALIDA_EVENTO, evento_nombre="Feria")
    service, repo, _, generador, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto(activo_ids=["a2"]))

    lineas = generador.generar_pdf.await_args.args[1]
    assert lineas == ["INV-1 - Activo a2"]
    assert repo.guardar.call_args.args[0].comprobante_archivo_id == "archivo-1"


async def test_el_prestamo_no_genera_comprobante(fabrica):
    service, repo, _, generador, _ = _servicio(fabrica, _movimiento(fabrica, n=1))

    await service.ejecutar(_dto())

    generador.generar_pdf.assert_not_called()
    assert repo.guardar.call_args.args[0].comprobante_archivo_id is None


async def test_si_falla_un_activo_se_deshacen_los_ya_cambiados_y_no_se_guarda(fabrica):
    movimiento = _movimiento(fabrica, n=2)
    service, repo, activo_movimiento, _, _ = _servicio(fabrica, movimiento)
    # a1 sale bien; en a2 falla el cambio de estado.
    activo_movimiento.cambiar_estado.side_effect = [True, False, True]

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()
    # Se devolvio a1 a su responsable y a disponible.
    activo_movimiento.cambiar_responsable.assert_any_await("a1", "u1", "u7", "Admin")
    activo_movimiento.cambiar_estado.assert_any_await("a1", "disponible", "u7", "Admin")


async def test_si_falla_el_responsable_se_deshace_el_estado_de_ese_activo(fabrica):
    service, repo, activo_movimiento, _, _ = _servicio(
        fabrica, _movimiento(fabrica, n=1), cambiar_responsable=False
    )

    with pytest.raises(OperacionSobreActivoFallidaError):
        await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_any_await("a1", "disponible", "u7", "Admin")
    repo.guardar.assert_not_called()


async def test_la_baja_no_se_confirma_como_salida(fabrica):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.BAJA, usuario_destino_id=None, items=[fabrica.item(estado=I.PENDIENTE_ADMIN)]
    )
    service, _, _, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())


async def test_un_movimiento_sin_activos_pendientes_no_se_confirma(fabrica):
    movimiento = fabrica.movimiento(items=[fabrica.item(estado=I.EN_CURSO)], estado=E.EN_CURSO)
    service, _, _, _, _ = _servicio(fabrica, movimiento)

    with pytest.raises(TransicionEstadoMovimientoInvalidaError):
        await service.ejecutar(_dto())


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, _movimiento(fabrica))
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())
