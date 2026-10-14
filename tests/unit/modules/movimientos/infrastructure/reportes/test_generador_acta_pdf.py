from datetime import UTC, datetime

from modules.movimientos.application.ports.generador_acta_port import DatosActaPdf, LineaActaPdf
from modules.movimientos.domain.entities import ResultadoChequeo as R
from modules.movimientos.domain.entities import TipoActa, TipoMovimiento
from modules.movimientos.infrastructure.reportes.generador_acta_pdf import GeneradorActaPdf


def _datos(fabrica, lineas=None, tipo=TipoActa.SALIDA, **acta):
    movimiento = fabrica.movimiento(
        tipo=TipoMovimiento.SALIDA_EVENTO,
        descripcion="Para la <b>feria</b>",
        evento_nombre="Feria anual",
        fecha_salida_estimada=datetime(2026, 1, 1, tzinfo=UTC),
    )
    lineas = lineas or [LineaActaPdf("INV-1 - Laptop Dell", R.ENCONTRADO, None)]

    return DatosActaPdf(
        movimiento=movimiento,
        acta=fabrica.acta(tipo=tipo, **acta),
        lineas=lineas,
        responsable_nombre="Ana Gomez",
        responsable_correo="ana@example.com",
    )


async def test_genera_un_pdf_valido_con_el_sello_pendiente(fabrica):
    contenido = await GeneradorActaPdf().generar_pdf(_datos(fabrica))

    assert contenido.startswith(b"%PDF")


async def test_genera_el_pdf_de_un_acta_aceptada_con_los_dos_sellos(fabrica):
    pendiente = await GeneradorActaPdf().generar_pdf(_datos(fabrica))
    aceptada = await GeneradorActaPdf().generar_pdf(
        _datos(fabrica, aceptada_por=fabrica.sello("u2", "Ana Gomez", "ana@example.com"))
    )

    assert aceptada.startswith(b"%PDF")
    # Cambia el contenido: el sello aceptado reemplaza al "pendiente".
    assert aceptada != pendiente


async def test_acta_de_ingreso_con_todos_los_resultados(fabrica):
    lineas = [
        LineaActaPdf("INV-1 - Laptop", R.ENCONTRADO, None),
        LineaActaPdf("INV-2 - Mesa", R.CON_NOVEDAD, "Pata rota"),
        LineaActaPdf("INV-3 - Silla", R.NO_ENCONTRADO, "Sigue fuera"),
    ]

    contenido = await GeneradorActaPdf().generar_pdf(_datos(fabrica, lineas, TipoActa.INGRESO, numero=2))

    assert contenido.startswith(b"%PDF")


async def test_con_muchos_activos_pagina_sin_fallar(fabrica):
    lineas = [LineaActaPdf(f"INV-{n} - Activo {n}", R.ENCONTRADO, "ok") for n in range(80)]

    contenido = await GeneradorActaPdf().generar_pdf(_datos(fabrica, lineas))

    assert contenido.startswith(b"%PDF")


async def test_los_textos_libres_con_marcas_no_rompen_el_pdf(fabrica):
    lineas = [LineaActaPdf("<b>Raro</b> & <i>nombre", R.CON_NOVEDAD, "<para>sin cerrar")]

    contenido = await GeneradorActaPdf().generar_pdf(_datos(fabrica, lineas))

    assert contenido.startswith(b"%PDF")
