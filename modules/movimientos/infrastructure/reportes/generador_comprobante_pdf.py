import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from xml.sax.saxutils import escape

from modules.movimientos.application.ports.generador_comprobante_port import (
    GeneradorComprobantePort,
)
from modules.movimientos.domain.entities import Movimiento


class GeneradorComprobantePdf(GeneradorComprobantePort):
    async def generar_pdf(
        self, movimiento: Movimiento, activos: list[str], usuario_destino_nombre: str
    ) -> bytes:
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=letter)
        estilos = getSampleStyleSheet()

        # Los textos libres se escapan: el PDF interpreta las marcas de reportlab que haya en ellos.
        elementos = [
            Paragraph("Comprobante de Salida de Activos", estilos["Title"]),
            Spacer(1, 0.5 * cm),
            Paragraph(f"<b>ID de movimiento:</b> {movimiento.id}", estilos["Normal"]),
            Paragraph(f"<b>Evento:</b> {escape(movimiento.evento_nombre or '-')}", estilos["Normal"]),
            Paragraph(f"<b>Entregado a:</b> {escape(usuario_destino_nombre)}", estilos["Normal"]),
            Paragraph(f"<b>Descripcion:</b> {escape(movimiento.descripcion)}", estilos["Normal"]),
            Paragraph(
                f"<b>Fecha de salida estimada:</b> {_fmt(movimiento.fecha_salida_estimada)}",
                estilos["Normal"],
            ),
            Paragraph(
                f"<b>Fecha de retorno estimada:</b> {_fmt(movimiento.fecha_retorno_estimada)}",
                estilos["Normal"],
            ),
            Paragraph(
                f"<b>Fecha de entrega real:</b> {_fmt(movimiento.fecha_entrega_real)}",
                estilos["Normal"],
            ),
            Spacer(1, 0.3 * cm),
            Paragraph(f"Activos que salen ({len(activos)})", estilos["Heading3"]),
            *[Paragraph(f"- {escape(activo)}", estilos["Normal"]) for activo in activos],
            Spacer(1, 0.3 * cm),
            Paragraph("Aprobaciones", estilos["Heading3"]),
            *_responsables(movimiento, estilos),
            Paragraph(
                f"Administrador general: {_nombre_aprobador(movimiento.aprobado_por_admin)}",
                estilos["Normal"],
            ),
            Paragraph(
                f"Solicitado por: {escape(movimiento.creado_por.nombre)} el {_fmt(movimiento.creado_por.fecha)}",
                estilos["Normal"],
            ),
        ]

        documento.build(elementos)
        return buffer.getvalue()


def _responsables(movimiento: Movimiento, estilos) -> list[Paragraph]:
    """Quien aprobo, como responsable, cada activo (sin repetir a la misma persona)."""
    nombres = list(
        dict.fromkeys(
            item.aprobado_por_responsable.nombre
            for item in movimiento.items
            if item.aprobado_por_responsable is not None
        )
    )
    texto = ", ".join(escape(nombre) for nombre in nombres) if nombres else "-"

    return [Paragraph(f"Responsables de los activos: {texto}", estilos["Normal"])]


def _fmt(fecha: datetime | None) -> str:
    return fecha.strftime("%d/%m/%Y %H:%M") if fecha else "-"


def _nombre_aprobador(aprobador) -> str:
    return escape(aprobador.nombre) if aprobador else "-"
