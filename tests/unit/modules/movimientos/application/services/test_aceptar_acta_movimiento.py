from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.chequeo_movimiento_dto import AceptarActaDTO
from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.resolutor_nombres_port import NombresReferenciasMovimiento
from modules.movimientos.application.services.aceptar_acta_movimiento import (
    AceptarActaMovimientoService,
)
from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.errors import (
    ActaNoEncontradaError,
    ActaYaAceptadaError,
    MovimientoNoEncontradoError,
    SoloElResponsableAceptaElActaError,
)


def _dto(actor_id="u2", acta_id="acta-1") -> AceptarActaDTO:
    return AceptarActaDTO(
        id_movimiento="m1", acta_id=acta_id, actor_id=actor_id, actor_nombre="Destino", actor_correo="destino@example.com"
    )


def _servicio(fabrica, **acta):
    movimiento = fabrica.movimiento(
        items=[fabrica.item(activo_id="a1", estado=I.EN_CURSO)],
        usuario_destino_id="u2",
        actas=[fabrica.acta(**acta)],
        comprobante_archivo_id="archivo-1",
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = movimiento
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = {"a1": fabrica.resumen()}
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMovimiento(
        usuarios={"u2": "Destino"}, correos={"u2": "destino@example.com"}
    )
    generador = AsyncMock()
    generador.generar_pdf.return_value = b"%PDF"
    almacen = AsyncMock()
    almacen.guardar.return_value = "archivo-2"
    notificador = AsyncMock()
    service = AceptarActaMovimientoService(
        repo, activo_movimiento, EmisorActas(generador, almacen, resolutor), notificador
    )

    return service, repo, generador, almacen, notificador


async def test_el_responsable_acepta_y_queda_su_sello_con_nombre_y_correo(fabrica):
    service, repo, _, _, _ = _servicio(fabrica)

    await service.ejecutar(_dto())

    [acta] = repo.guardar.call_args.args[0].actas
    assert acta.aceptada_por.id_persona == "u2"
    assert acta.aceptada_por.nombre == "Destino"
    assert acta.aceptada_por.correo == "destino@example.com"
    assert acta.aceptada_por.fecha is not None
    # El sello de administracion no cambia.
    assert acta.cerrada_por.nombre == "Admin"


async def test_el_pdf_se_vuelve_a_emitir_con_los_dos_sellos_y_se_borra_el_anterior(fabrica):
    service, repo, generador, almacen, _ = _servicio(fabrica)

    await service.ejecutar(_dto())

    assert generador.generar_pdf.await_args.args[0].acta.aceptada_por is not None
    almacen.eliminar.assert_awaited_once_with("archivo-1")
    guardado = repo.guardar.call_args.args[0]
    assert guardado.actas[0].archivo_id == "archivo-2"
    # El comprobante historico apunta al PDF vigente.
    assert guardado.comprobante_archivo_id == "archivo-2"


async def test_el_comprobante_de_otra_acta_no_se_toca(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, archivo_id="archivo-distinto")

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].comprobante_archivo_id == "archivo-1"


async def test_se_avisa_que_el_acta_quedo_completa(fabrica):
    service, _, _, _, notificador = _servicio(fabrica)

    await service.ejecutar(_dto())

    notificador.notificar.assert_awaited_once()
    asunto = notificador.notificar.await_args.kwargs["asunto"]
    assert "Acta de salida No. 1 aceptada" in asunto


@pytest.mark.parametrize("actor", ["u7", "u1", "u9"])
async def test_solo_el_destinatario_acepta(fabrica, actor):
    service, repo, _, _, _ = _servicio(fabrica)

    with pytest.raises(SoloElResponsableAceptaElActaError):
        await service.ejecutar(_dto(actor_id=actor))

    repo.guardar.assert_not_called()


async def test_un_acta_ya_aceptada_no_se_acepta_de_nuevo(fabrica):
    service, repo, _, _, _ = _servicio(fabrica, aceptada_por=fabrica.sello("u2", "Destino", "destino@example.com"))

    with pytest.raises(ActaYaAceptadaError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_un_acta_inexistente_falla(fabrica):
    service, _, _, _, _ = _servicio(fabrica)

    with pytest.raises(ActaNoEncontradaError):
        await service.ejecutar(_dto(acta_id="nada"))


async def test_un_movimiento_inexistente_falla(fabrica):
    service, repo, _, _, _ = _servicio(fabrica)
    repo.obtener_por_id.return_value = None

    with pytest.raises(MovimientoNoEncontradoError):
        await service.ejecutar(_dto())


async def test_solo_se_acepta_la_acta_pedida_y_las_demas_quedan_igual(fabrica):
    service, repo, _, _, _ = _servicio(fabrica)
    otra = fabrica.acta(id="acta-2", numero=2)
    repo.obtener_por_id.return_value = replace(
        repo.obtener_por_id.return_value, actas=[*repo.obtener_por_id.return_value.actas, otra]
    )

    await service.ejecutar(_dto())

    primera, segunda = repo.guardar.call_args.args[0].actas
    assert primera.aceptada_por is not None
    assert segunda.aceptada_por is None
