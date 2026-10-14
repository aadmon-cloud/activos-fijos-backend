from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarSalidaDTO
from modules.movimientos.application.emisor_actas import EmisorActas
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
from modules.movimientos.domain.entities import EtapaRechazo, ResultadoChequeo as R, TipoActa, TipoMovimiento
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    NingunActivoChequeadoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)


def _dto(motivo=None) -> ConfirmarSalidaDTO:
    return ConfirmarSalidaDTO(
        id_movimiento="m1", actor_id="u7", actor_nombre="Admin", actor_correo="admin@example.com", motivo_no_incluidos=motivo
    )


def _movimiento(fabrica, resultados=(R.ENCONTRADO,) * 3, **overrides):
    """Un item por resultado; `None` es un activo que nadie chequeo."""
    items = [
        fabrica.item(
            activo_id=f"a{k}",
            responsable_original_id="u1",
            estado=I.PENDIENTE_ADMIN,
            chequeo_salida=fabrica.chequeo(resultado) if resultado else None,
        )
        for k, resultado in enumerate(resultados, start=1)
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
    resolutor.resolver.return_value = NombresReferenciasMovimiento(
        usuarios={"u2": "Destino"}, correos={"u2": "destino@example.com"}
    )
    generador = AsyncMock()
    generador.generar_pdf.return_value = b"%PDF"
    almacen = AsyncMock()
    almacen.guardar.return_value = "archivo-1"
    notificador = AsyncMock()
    service = ConfirmarSalidaMovimientoService(
        repo, activo_movimiento, EmisorActas(generador, almacen, resolutor), notificador
    )

    return service, repo, activo_movimiento, generador, notificador


async def test_salen_los_chequeados_como_encontrados_o_con_novedad(fabrica):
    movimiento = _movimiento(fabrica, (R.ENCONTRADO, R.CON_NOVEDAD))
    service, repo, activo_movimiento, _, notificador = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.EN_CURSO] * 2
    assert guardado.estado == E.EN_CURSO
    assert guardado.aprobado_por_admin.id_persona == "u7"
    assert guardado.fecha_entrega_real is not None
    assert activo_movimiento.cambiar_estado.await_count == 2
    activo_movimiento.cambiar_responsable.assert_any_await("a1", "u2", "u7", "Admin")
    notificador.notificar.assert_awaited_once()


async def test_el_activo_pasa_a_prestado_a_cargo_del_destinatario(fabrica):
    service, _, activo_movimiento, _, _ = _servicio(fabrica, _movimiento(fabrica, (R.ENCONTRADO,)))

    await service.ejecutar(_dto())

    activo_movimiento.cambiar_estado.assert_awaited_once_with("a1", "prestado", "u7", "Admin")
    activo_movimiento.cambiar_responsable.assert_awaited_once_with("a1", "u2", "u7", "Admin")


async def test_lo_no_encontrado_y_lo_no_chequeado_quedan_rechazados_por_administracion(fabrica):
    movimiento = _movimiento(fabrica, (R.ENCONTRADO, R.NO_ENCONTRADO, None))
    movimiento = replace(
        movimiento,
        items=[
            movimiento.items[0],
            replace(movimiento.items[1], chequeo_salida=fabrica.chequeo(R.NO_ENCONTRADO, "No estaba en bodega")),
            movimiento.items[2],
        ],
    )
    service, repo, activo_movimiento, _, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto(motivo="Sin revisar"))

    guardado = repo.guardar.call_args.args[0]
    assert [i.estado for i in guardado.items] == [I.EN_CURSO, I.RECHAZADO, I.RECHAZADO]
    assert guardado.item("a2").etapa_rechazo == EtapaRechazo.ADMINISTRACION
    assert guardado.item("a2").rechazado_por.id_persona == "u7"
    # El motivo propio del chequeo manda sobre el general.
    assert guardado.item("a2").motivo_rechazo == "No estaba en bodega"
    assert guardado.item("a3").motivo_rechazo == "Sin revisar"
    assert activo_movimiento.cambiar_estado.await_count == 1


async def test_los_que_no_salen_llevan_un_motivo_por_defecto(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, _movimiento(fabrica, (R.ENCONTRADO, None)))

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].item("a2").motivo_rechazo


async def test_sin_ningun_activo_encontrado_no_se_cierra_el_chequeo(fabrica):
    service, repo, activo_movimiento, _, _ = _servicio(fabrica, _movimiento(fabrica, (R.NO_ENCONTRADO, None)))

    with pytest.raises(NingunActivoChequeadoError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()
    activo_movimiento.cambiar_estado.assert_not_called()


async def test_solo_se_confirman_los_activos_que_esperan_a_administracion(fabrica):
    movimiento = _movimiento(fabrica, (R.ENCONTRADO,))
    items = [movimiento.items[0], fabrica.item(activo_id="a2", estado=I.RECHAZADO)]
    service, repo, _, _, _ = _servicio(fabrica, replace(movimiento, items=items))

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    assert guardado.item("a1").estado == I.EN_CURSO
    assert guardado.item("a2").estado == I.RECHAZADO


async def test_se_genera_el_acta_de_salida_con_el_sello_de_administracion(fabrica):
    movimiento = _movimiento(fabrica, (R.ENCONTRADO, R.CON_NOVEDAD), tipo=TipoMovimiento.SALIDA_EVENTO, evento_nombre="Feria")
    service, repo, _, generador, _ = _servicio(fabrica, movimiento)

    await service.ejecutar(_dto())

    guardado = repo.guardar.call_args.args[0]
    [acta] = guardado.actas
    assert (acta.tipo, acta.numero) == (TipoActa.SALIDA, 1)
    assert [(l.activo_id, l.resultado) for l in acta.lineas] == [("a1", R.ENCONTRADO), ("a2", R.CON_NOVEDAD)]
    assert acta.cerrada_por.nombre == "Admin"
    assert acta.cerrada_por.correo == "admin@example.com"
    assert acta.aceptada_por is None
    assert acta.archivo_id == "archivo-1"
    assert guardado.comprobante_archivo_id == "archivo-1"

    datos = generador.generar_pdf.await_args.args[0]
    assert datos.responsable_nombre == "Destino"
    assert datos.responsable_correo == "destino@example.com"
    assert [l.descripcion for l in datos.lineas] == ["a1", "a2"]


async def test_el_acta_lista_tambien_lo_que_no_salio_con_su_motivo(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, _movimiento(fabrica, (R.ENCONTRADO, None)))

    await service.ejecutar(_dto(motivo="Sin revisar"))

    [acta] = repo.guardar.call_args.args[0].actas
    assert [(l.activo_id, l.resultado, l.observacion) for l in acta.lineas] == [
        ("a1", R.ENCONTRADO, None),
        ("a2", R.NO_ENCONTRADO, "Sin revisar"),
    ]


async def test_el_prestamo_tambien_genera_acta(fabrica):
    service, repo, _, generador, _ = _servicio(fabrica, _movimiento(fabrica, (R.ENCONTRADO,)))

    await service.ejecutar(_dto())

    generador.generar_pdf.assert_awaited_once()
    assert len(repo.guardar.call_args.args[0].actas) == 1


async def test_si_falla_un_activo_se_deshacen_los_ya_cambiados_y_no_se_guarda(fabrica):
    service, repo, activo_movimiento, _, _ = _servicio(fabrica, _movimiento(fabrica, (R.ENCONTRADO,) * 2))
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
        fabrica, _movimiento(fabrica, (R.ENCONTRADO,)), cambiar_responsable=False
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
