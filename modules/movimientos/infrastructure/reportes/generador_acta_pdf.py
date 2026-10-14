import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.movimientos.application.ports.generador_acta_port import (
    DatosActaPdf,
    GeneradorActaPort,
)
from modules.movimientos.domain.entities import (
    ResultadoChequeo,
    SelloActa,
    TipoActa,
    TipoMovimiento,
)

_TITULO = {TipoActa.SALIDA: "Acta de salida de activos", TipoActa.INGRESO: "Acta de ingreso de activos"}
_ETIQUETA_TIPO = {TipoMovimiento.PRESTAMO: "Préstamo", TipoMovimiento.SALIDA_EVENTO: "Salida a evento"}

# Lo que significa cada resultado segun la fase: en la salida "encontrado" es que sale; en el ingreso, que se recibe.
_RESULTADO = {
    TipoActa.SALIDA: {
        ResultadoChequeo.ENCONTRADO: "Salió",
        ResultadoChequeo.CON_NOVEDAD: "Salió con novedad",
        ResultadoChequeo.NO_ENCONTRADO: "No salió",
    },
    TipoActa.INGRESO: {
        ResultadoChequeo.ENCONTRADO: "Recibido",
        ResultadoChequeo.CON_NOVEDAD: "Recibido con novedad",
        ResultadoChequeo.NO_ENCONTRADO: "No devuelto",
    },
}

_ROL_RESPONSABLE = {TipoActa.SALIDA: "Responsable que retira", TipoActa.INGRESO: "Responsable que devuelve"}
_ROL_ADMIN = {TipoActa.SALIDA: "Administrador general que entrega", TipoActa.INGRESO: "Administrador general que recibe"}

_COLOR_SELLO = colors.HexColor("#0B3D91")
_COLOR_PENDIENTE = colors.HexColor("#9A6700")


class GeneradorActaPdf(GeneradorActaPort):
    async def generar_pdf(self, datos: DatosActaPdf) -> bytes:
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=letter)
        estilos = getSampleStyleSheet()
        movimiento, acta = datos.movimiento, datos.acta
        normal = estilos["Normal"]

        # Los textos libres se escapan: el PDF interpreta las marcas de reportlab que haya en ellos.
        elementos = [
            Paragraph(f"{_TITULO[acta.tipo]} No. {acta.numero}", estilos["Title"]),
            Spacer(1, 0.4 * cm),
            Paragraph(f"<b>Movimiento:</b> {movimiento.id}", normal),
            Paragraph(f"<b>Tipo:</b> {_ETIQUETA_TIPO.get(movimiento.tipo, movimiento.tipo.value)}", normal),
            Paragraph(f"<b>Evento:</b> {escape(movimiento.evento_nombre or '-')}", normal),
            Paragraph(f"<b>Descripción:</b> {escape(movimiento.descripcion)}", normal),
            Paragraph(f"<b>Salida estimada:</b> {_fmt(movimiento.fecha_salida_estimada)}", normal),
            Paragraph(f"<b>Retorno estimado:</b> {_fmt(movimiento.fecha_retorno_estimada)}", normal),
            Paragraph(f"<b>Fecha del acta:</b> {_fmt(acta.cerrada_por.fecha)}", normal),
            Spacer(1, 0.5 * cm),
            Paragraph(f"Activos ({len(datos.lineas)})", estilos["Heading3"]),
            _tabla_activos(datos, estilos),
            Spacer(1, 1.2 * cm),
            _sellos(datos, estilos),
        ]

        documento.build(elementos)
        return buffer.getvalue()


def _tabla_activos(datos: DatosActaPdf, estilos) -> Table:
    celda = ParagraphStyle("celda", parent=estilos["Normal"], fontSize=9, leading=11)
    etiquetas = _RESULTADO[datos.acta.tipo]
    filas = [[Paragraph(f"<b>{texto}</b>", celda) for texto in ("Activo", "Resultado", "Observación")]]
    for linea in datos.lineas:
        filas.append(
            [
                Paragraph(escape(linea.descripcion), celda),
                Paragraph(etiquetas[linea.resultado], celda),
                Paragraph(escape(linea.observacion or "-"), celda),
            ]
        )

    tabla = Table(filas, colWidths=[7 * cm, 3.5 * cm, 7 * cm], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return tabla


def _sellos(datos: DatosActaPdf, estilos) -> Table:
    acta = datos.acta
    sello_responsable = _sello(
        _ROL_RESPONSABLE[acta.tipo],
        acta.aceptada_por,
        datos.responsable_nombre,
        datos.responsable_correo,
        estilos,
        "Aceptado",
    )
    sello_admin = _sello(
        _ROL_ADMIN[acta.tipo], acta.cerrada_por, acta.cerrada_por.nombre, acta.cerrada_por.correo, estilos, "Firmado"
    )

    tabla = Table([[sello_responsable, sello_admin]], colWidths=[9 * cm, 9 * cm])
    tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    return tabla


def _sello(rol: str, sello: SelloActa | None, nombre: str, correo: str, estilos, accion: str) -> Table:
    """Recuadro tipo sello con nombre y correo. Sin firma aun, queda marcado como pendiente de aceptacion."""
    color = _COLOR_SELLO if sello else _COLOR_PENDIENTE
    estado = f"{accion} el {_fmt(sello.fecha)}" if sello else "PENDIENTE DE ACEPTACIÓN"
    base = ParagraphStyle("sello", parent=estilos["Normal"], fontSize=9, leading=12, textColor=color)

    contenido = [
        [Paragraph(f"<b>{escape(rol)}</b>", base)],
        [Paragraph(f"<b>{escape(nombre)}</b>", base)],
        [Paragraph(escape(correo), base)],
        [Paragraph(estado, base)],
    ]
    caja = Table(contenido, colWidths=[8 * cm])
    caja.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.5, color),
                ("INNERPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return caja


def _fmt(fecha: datetime | None) -> str:
    return fecha.strftime("%d/%m/%Y %H:%M") if fecha else "-"
