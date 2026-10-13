import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.auditorias.application.ports.generador_reporte_port import GeneradorReportePort
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.domain.entities import Auditoria, ItemAuditoria, ResultadoVerificacion

_ETIQUETAS_RESULTADO = {
    ResultadoVerificacion.ENCONTRADO: "Encontrado",
    ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD: "Encontrado con novedad",
    ResultadoVerificacion.NO_ENCONTRADO: "No encontrado",
}


class GeneradorReportePdf(GeneradorReportePort):
    async def generar_pdf(self, auditoria: Auditoria, usuario: UsuarioAuditado) -> bytes:
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=letter)
        estilos = getSampleStyleSheet()

        encontrados = [i for i in auditoria.items if i.resultado == ResultadoVerificacion.ENCONTRADO]
        con_novedad = [
            i for i in auditoria.items if i.resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD
        ]
        faltantes = [i for i in auditoria.items if i.resultado == ResultadoVerificacion.NO_ENCONTRADO]

        elementos = [
            Paragraph("Auditoria de Activos y Elementos", estilos["Title"]),
            Spacer(1, 0.5 * cm),
            Paragraph(f"<b>ID de auditoria:</b> {auditoria.id}", estilos["Normal"]),
            Paragraph(f"<b>Fecha de inicio:</b> {_fmt(auditoria.creado_por.fecha)}", estilos["Normal"]),
            Paragraph(f"<b>Fecha de finalizacion:</b> {_fmt(auditoria.fecha_cierre)}", estilos["Normal"]),
            Paragraph(f"<b>Auditor:</b> {auditoria.creado_por.nombre}", estilos["Normal"]),
            Spacer(1, 0.3 * cm),
            Paragraph("Usuario auditado", estilos["Heading3"]),
            Paragraph(f"Nombre: {usuario.nombre_completo}", estilos["Normal"]),
            Paragraph(f"Identificacion: {usuario.identificacion or '-'}", estilos["Normal"]),
            Paragraph(f"Correo: {usuario.email}", estilos["Normal"]),
            Spacer(1, 0.3 * cm),
            Paragraph("Resumen", estilos["Heading3"]),
            Paragraph(f"Total de elementos auditados: {len(auditoria.items)}", estilos["Normal"]),
            Paragraph(f"Encontrados: {len(encontrados)}", estilos["Normal"]),
            Paragraph(f"Encontrados con novedad: {len(con_novedad)}", estilos["Normal"]),
            Paragraph(f"No encontrados: {len(faltantes)}", estilos["Normal"]),
            Spacer(1, 0.3 * cm),
            Paragraph("Detalle", estilos["Heading3"]),
            _tabla_detalle(auditoria.items),
        ]

        if faltantes:
            elementos.append(Spacer(1, 0.3 * cm))
            elementos.append(Paragraph("Reporte de Faltantes", estilos["Heading3"]))
            elementos.append(_tabla_detalle(faltantes))

        documento.build(elementos)
        return buffer.getvalue()


def _fmt(fecha: datetime | None) -> str:
    return fecha.strftime("%d/%m/%Y %H:%M") if fecha else "-"


def _tabla_detalle(items: list[ItemAuditoria]) -> Table:
    encabezado = ["Tipo", "Nombre", "Codigo", "Serial", "Resultado", "Observacion"]
    filas = [encabezado]
    for item in items:
        filas.append(
            [
                item.tipo,
                item.nombre,
                item.numero_inventario,
                item.serie or "-",
                _ETIQUETAS_RESULTADO.get(item.resultado, "-"),
                item.observacion or "-",
            ]
        )

    tabla = Table(filas, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tabla
