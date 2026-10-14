from unittest.mock import AsyncMock

from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ActivoNombreMovimiento,
    NombresReferenciasMovimiento,
)
from modules.movimientos.domain.entities import LineaActa, ResultadoChequeo as R, TipoActa


def _emisor(nombres=None):
    resolutor = AsyncMock()
    resolutor.resolver.return_value = nombres or NombresReferenciasMovimiento(
        activos={"a1": ActivoNombreMovimiento("Proyector", "INV-1"), "a2": ActivoNombreMovimiento("Pantalla", "")},
        usuarios={"u2": "Destino"},
        correos={"u2": "destino@example.com"},
    )
    generador = AsyncMock()
    generador.generar_pdf.return_value = b"%PDF"
    almacen = AsyncMock()
    almacen.guardar.return_value = "archivo-nuevo"

    return EmisorActas(generador, almacen, resolutor), generador, almacen, resolutor


async def test_emitir_crea_el_acta_con_el_sello_de_administracion_y_guarda_el_pdf(fabrica):
    emisor, _, almacen, _ = _emisor()
    movimiento = fabrica.movimiento(usuario_destino_id="u2")
    lineas = [LineaActa(activo_id="a1", resultado=R.ENCONTRADO)]

    acta = await emisor.emitir(movimiento, TipoActa.SALIDA, lineas, fabrica.sello())

    assert acta.tipo == TipoActa.SALIDA and acta.numero == 1
    assert acta.id and acta.lineas == lineas
    assert acta.cerrada_por.nombre == "Admin" and acta.aceptada_por is None
    assert acta.archivo_id == "archivo-nuevo"
    almacen.guardar.assert_awaited_once_with("m1", "acta-salida-1.pdf", b"%PDF", "application/pdf")


async def test_el_consecutivo_cuenta_las_actas_del_mismo_tipo(fabrica):
    emisor, _, almacen, _ = _emisor()
    movimiento = fabrica.movimiento(
        usuario_destino_id="u2",
        actas=[fabrica.acta(id="s1"), fabrica.acta(id="i1", tipo=TipoActa.INGRESO), fabrica.acta(id="i2", tipo=TipoActa.INGRESO)],
    )

    ingreso = await emisor.emitir(movimiento, TipoActa.INGRESO, [], fabrica.sello())
    salida = await emisor.emitir(movimiento, TipoActa.SALIDA, [], fabrica.sello())

    assert (ingreso.numero, salida.numero) == (3, 2)
    assert almacen.guardar.await_args_list[0].args[1] == "acta-ingreso-3.pdf"


async def test_el_pdf_lleva_nombre_e_inventario_y_los_datos_del_responsable(fabrica):
    emisor, generador, _, _ = _emisor()
    movimiento = fabrica.movimiento(usuario_destino_id="u2")
    lineas = [LineaActa(activo_id="a1", resultado=R.CON_NOVEDAD, observacion="Rayado"), LineaActa(activo_id="a2", resultado=R.ENCONTRADO), LineaActa(activo_id="a9", resultado=R.NO_ENCONTRADO)]

    await emisor.emitir(movimiento, TipoActa.SALIDA, lineas, fabrica.sello())

    datos = generador.generar_pdf.await_args.args[0]
    # Sin inventario solo el nombre; un activo que ya no existe se identifica por su id.
    assert [(l.descripcion, l.resultado, l.observacion) for l in datos.lineas] == [
        ("INV-1 - Proyector", R.CON_NOVEDAD, "Rayado"),
        ("Pantalla", R.ENCONTRADO, None),
        ("a9", R.NO_ENCONTRADO, None),
    ]
    assert (datos.responsable_nombre, datos.responsable_correo) == ("Destino", "destino@example.com")


async def test_sin_destinatario_el_sello_del_responsable_va_con_guiones(fabrica):
    emisor, generador, _, resolutor = _emisor(NombresReferenciasMovimiento())
    movimiento = fabrica.movimiento(usuario_destino_id=None)

    await emisor.emitir(movimiento, TipoActa.SALIDA, [], fabrica.sello())

    datos = generador.generar_pdf.await_args.args[0]
    assert (datos.responsable_nombre, datos.responsable_correo) == ("-", "-")
    assert resolutor.resolver.await_args.args[0].usuario_ids == set()


async def test_aceptar_reimprime_con_el_sello_del_responsable_y_borra_el_pdf_anterior(fabrica):
    emisor, generador, almacen, _ = _emisor()
    movimiento = fabrica.movimiento(usuario_destino_id="u2")
    acta = fabrica.acta(archivo_id="viejo")

    aceptada = await emisor.aceptar(movimiento, acta, fabrica.sello("u2", "Destino", "destino@example.com"))

    assert aceptada.aceptada_por.correo == "destino@example.com"
    assert aceptada.archivo_id == "archivo-nuevo"
    assert generador.generar_pdf.await_args.args[0].acta.aceptada_por is not None
    almacen.eliminar.assert_awaited_once_with("viejo")


async def test_aceptar_un_acta_sin_pdf_previo_no_borra_nada(fabrica):
    emisor, _, almacen, _ = _emisor()

    await emisor.aceptar(fabrica.movimiento(usuario_destino_id="u2"), fabrica.acta(archivo_id=None), fabrica.sello())

    almacen.eliminar.assert_not_called()
