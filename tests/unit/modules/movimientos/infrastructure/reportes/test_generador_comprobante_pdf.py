from datetime import UTC, datetime

from modules.movimientos.domain.entities import EstadoItemMovimiento, TipoMovimiento
from modules.movimientos.infrastructure.reportes.generador_comprobante_pdf import (
    GeneradorComprobantePdf,
)


def _movimiento(fabrica, **overrides):
    valores = dict(
        tipo=TipoMovimiento.SALIDA_EVENTO,
        descripcion="Necesario para la feria",
        evento_nombre="Feria anual",
        fecha_salida_estimada=datetime(2026, 1, 1, tzinfo=UTC),
        fecha_retorno_estimada=datetime(2026, 1, 5, tzinfo=UTC),
        fecha_entrega_real=datetime(2026, 1, 1, 10, tzinfo=UTC),
        aprobado_por_admin=fabrica.audit("admin-1", "Admin"),
        items=[
            fabrica.item(
                estado=EstadoItemMovimiento.EN_CURSO, aprobado_por_responsable=fabrica.audit("r1", "Responsable")
            )
        ],
    )
    valores.update(overrides)

    return fabrica.movimiento(**valores)


async def test_generar_pdf_retorna_bytes_de_un_pdf_valido(fabrica):
    contenido = await GeneradorComprobantePdf().generar_pdf(
        _movimiento(fabrica), ["INV-1 - Laptop Dell"], "Usuario Destino"
    )

    assert contenido.startswith(b"%PDF")


async def test_generar_pdf_con_varios_activos(fabrica):
    lineas = [f"INV-{n} - Activo {n}" for n in range(30)]

    contenido = await GeneradorComprobantePdf().generar_pdf(_movimiento(fabrica), lineas, "Usuario Destino")

    assert contenido.startswith(b"%PDF")


async def test_generar_pdf_funciona_sin_aprobaciones_registradas(fabrica):
    movimiento = _movimiento(fabrica, aprobado_por_admin=None, items=[fabrica.item()])

    contenido = await GeneradorComprobantePdf().generar_pdf(movimiento, ["Laptop Dell"], "Usuario Destino")

    assert contenido.startswith(b"%PDF")


async def test_generar_pdf_escapa_los_textos_libres(fabrica):
    # Un "<" suelto en un texto libre romperia el documento si no se escapara.
    movimiento = _movimiento(fabrica, descripcion="Cables <rojos> & azules", evento_nombre="Feria <1>")

    contenido = await GeneradorComprobantePdf().generar_pdf(movimiento, ["Cable <A>"], "Ana <B>")

    assert contenido.startswith(b"%PDF")
