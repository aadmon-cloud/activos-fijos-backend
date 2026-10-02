import asyncio
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

from modules.movimientos.application.ports.comprobante import ComprobantePort
from modules.movimientos.domain.entities.movimiento import Movimiento

_MODALIDADES_MULTI_PRODUCTO = {"kit", "multiple", "mercado"}


class ReportlabComprobanteAdapter(ComprobantePort):
    """Comprobante de salida (individual, kit, múltiple o mercado) — mismo
    formato visual que el legacy (`app/utils/pdf_generator.py::generar_comprobante_salida`),
    reescrito para leer de `Movimiento` en vez de dicts sueltos."""

    def __init__(self):
        self._styles = getSampleStyleSheet()

    async def generar_comprobante_salida(self, movimiento: Movimiento) -> bytes:
        return await asyncio.to_thread(self._generar, movimiento)

    def _generar(self, movimiento: Movimiento) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        es_multi_producto = movimiento.modalidad in _MODALIDADES_MULTI_PRODUCTO
        productos_data = self._productos_data(movimiento, es_multi_producto)
        nombre_bundle = movimiento.kit_nombre or movimiento.nombre_mercado

        story = []
        story.extend(self._encabezado())
        story.append(Spacer(1, 1 * cm))
        story.extend(self._info_salida(movimiento))
        story.append(Spacer(1, 0.5 * cm))
        story.extend(self._tabla_productos(productos_data, es_multi_producto, nombre_bundle))
        story.append(Spacer(1, 1 * cm))
        if movimiento.notas:
            story.extend(self._observaciones(movimiento.notas))
            story.append(Spacer(1, 0.5 * cm))
        story.extend(self._seccion_firmas())
        story.append(Spacer(1, 1 * cm))
        story.extend(self._pie_pagina())

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _productos_data(self, movimiento: Movimiento, es_multi_producto: bool) -> list[dict]:
        if es_multi_producto:
            return [
                {
                    "producto_nombre": item.producto_nombre,
                    "producto_codigo": item.producto_codigo,
                    "cantidad_por_kit": item.cantidad,
                    "cantidad_total": item.cantidad,
                }
                for item in (movimiento.productos or [])
            ]
        return [
            {
                "producto_nombre": movimiento.producto_nombre or "Producto",
                "producto_codigo": movimiento.producto_codigo or "N/A",
                "cantidad": movimiento.cantidad,
            }
        ]

    def _encabezado(self) -> list:
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=self._styles["Heading1"],
            fontSize=18,
            alignment=1,
            spaceAfter=6,
            textColor=colors.HexColor("#1a3d7c"),
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "SubtitleStyle",
            parent=self._styles["Heading2"],
            fontSize=14,
            alignment=1,
            spaceAfter=12,
            textColor=colors.HexColor("#2c5282"),
            fontName="Helvetica",
        )
        return [
            Paragraph("FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO", title_style),
            Paragraph("FIMLM", subtitle_style),
            Paragraph("COMPROBANTE DE SALIDA DE INVENTARIO", subtitle_style),
            Spacer(1, 0.2 * cm),
            self._linea_divisoria(),
        ]

    def _info_salida(self, movimiento: Movimiento) -> list:
        info_style = ParagraphStyle(
            "InfoStyle", parent=self._styles["Normal"], fontSize=10, leading=12, spaceAfter=3
        )
        fecha = movimiento.creado_por.fecha.strftime("%d/%m/%Y %H:%M:%S")
        texto = (
            f"<b>FECHA Y HORA:</b> {fecha}<br/>"
            f"<b>DESTINO/RESPONSABLE:</b> {movimiento.cliente_destino or 'No especificado'}<br/>"
            f"<b>NÚMERO DE REMISIÓN (RM):</b> {movimiento.remision or 'N/A'}<br/>"
            f"<b>NÚMERO DE CASO:</b> {movimiento.caso or 'N/A'}<br/>"
            f"<b>NÚMERO DE CAJAS:</b> {movimiento.numero_cajas if movimiento.numero_cajas is not None else 'N/A'}<br/>"
        )
        if movimiento.kit_nombre:
            texto += f"<b>NOMBRE DEL KIT:</b> {movimiento.kit_nombre}<br/>"
        if movimiento.nombre_mercado:
            texto += f"<b>MERCADO PREDEFINIDO:</b> {movimiento.nombre_mercado}<br/>"
        if movimiento.referencia:
            texto += f"<b>REFERENCIA:</b> {movimiento.referencia}<br/>"
        texto += f"<b>REGISTRADO POR:</b> {movimiento.creado_por.nombre}"
        return [Paragraph(texto, info_style)]

    def _tabla_productos(
        self, productos_data: list[dict], es_multi_producto: bool, nombre_bundle: str | None
    ) -> list:
        title_style = ParagraphStyle(
            "TableTitle", parent=self._styles["Heading3"], fontSize=12, spaceAfter=8
        )
        titulo = f"PRODUCTOS DE: {nombre_bundle}" if nombre_bundle else "PRODUCTOS"
        elements: list = [Paragraph(titulo, title_style)]

        headers = (
            ["No.", "CÓDIGO", "DESCRIPCIÓN", "UNID/KIT", "TOTAL"]
            if es_multi_producto
            else ["No.", "CÓDIGO", "DESCRIPCIÓN", "CANTIDAD"]
        )
        table_data = [headers]
        total_general = 0
        for i, producto in enumerate(productos_data, 1):
            if es_multi_producto:
                cantidad_total = producto.get("cantidad_total", 0)
                fila = [
                    str(i),
                    producto.get("producto_codigo", "N/A"),
                    producto.get("producto_nombre", "Producto"),
                    str(producto.get("cantidad_por_kit", 0)),
                    str(cantidad_total),
                ]
                total_general += cantidad_total
            else:
                cantidad = producto.get("cantidad", 0)
                fila = [
                    str(i),
                    producto.get("producto_codigo", "N/A"),
                    producto.get("producto_nombre", "Producto"),
                    str(cantidad),
                ]
                total_general += cantidad
            table_data.append(fila)

        fila_total = (
            ["", "", "TOTAL GENERAL", "", str(total_general)]
            if es_multi_producto
            else ["", "", "TOTAL", str(total_general)]
        )
        table_data.append(fila_total)

        col_widths = (
            [1 * cm, 2.5 * cm, 7 * cm, 2 * cm, 2 * cm]
            if es_multi_producto
            else [1 * cm, 2.5 * cm, 9 * cm, 2.5 * cm]
        )
        tabla = Table(table_data, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3d7c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
                    ("BOX", (0, -1), (-1, -1), 1.5, colors.black),
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("ALIGN", (-1, 1), (-1, -2), "CENTER"),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (-1, -1), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(tabla)
        return elements

    def _observaciones(self, notas: str) -> list:
        obs_style = ParagraphStyle(
            "ObservacionesStyle",
            parent=self._styles["Normal"],
            fontSize=9,
            leading=11,
            backColor=colors.HexColor("#f8f9fa"),
            borderPadding=8,
            borderWidth=1,
            borderColor=colors.grey,
            borderRadius=3,
        )
        return [Paragraph(f"<b>OBSERVACIONES / NOTAS ADICIONALES:</b><br/>{notas}", obs_style)]

    def _seccion_firmas(self) -> list:
        title_style = ParagraphStyle(
            "FirmasTitle",
            parent=self._styles["Heading3"],
            fontSize=11,
            spaceAfter=15,
            alignment=1,
        )
        firmas_data = [
            ["ENTREGADO POR:", "RECIBIDO POR:"],
            ["", ""],
            ["_________________________", "_________________________"],
            ["Nombre y Apellido", "Nombre y Apellido"],
            ["", ""],
            ["_________________________", "_________________________"],
            ["C.C./NIT", "C.C./NIT"],
            ["", ""],
            ["_________________________", "_________________________"],
            ["Firma / Sello", "Firma / Sello"],
        ]
        tabla = Table(firmas_data, colWidths=[8 * cm, 8 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return [Paragraph("FIRMAS Y SELLOS", title_style), tabla]

    def _pie_pagina(self) -> list:
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=self._styles["Normal"],
            fontSize=8,
            alignment=1,
            textColor=colors.grey,
            spaceBefore=10,
        )
        texto = (
            "<b>FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO - FIMLM</b><br/>"
            "Sistema de Gestión de Inventarios • Documento generado automáticamente"
        )
        return [self._linea_divisoria(), Paragraph(texto, footer_style)]

    def _linea_divisoria(self):
        return HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a3d7c"))
