# app/utils/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from datetime import datetime
import io
import os

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.page_size = A4
        
    def generar_comprobante_salida(self, salida_data, productos_data):
        """
        Genera un comprobante de salida PDF.
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=self.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # 1. ENCABEZADO
        story.extend(self._crear_encabezado())
        story.append(Spacer(1, 1*cm))
        
        # 2. INFORMACIÓN DE LA SALIDA
        story.extend(self._crear_info_salida(salida_data))
        story.append(Spacer(1, 0.5*cm))
        
        # 3. TABLA DE PRODUCTOS
        story.extend(self._crear_tabla_productos(productos_data, salida_data))
        story.append(Spacer(1, 1*cm))
        
        # 4. OBSERVACIONES
        if salida_data.get('observaciones'):
            story.extend(self._crear_observaciones(salida_data['observaciones']))
            story.append(Spacer(1, 0.5*cm))
        
        # 5. FIRMAS
        story.extend(self._crear_seccion_firmas())
        
        # 6. PIE DE PÁGINA
        story.append(Spacer(1, 1*cm))
        story.extend(self._crear_pie_pagina())
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _crear_encabezado(self):
        """Crea el encabezado con logo y título."""
        elements = []
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=1,
            spaceAfter=6,
            textColor=colors.HexColor('#1a3d7c'),
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=1,
            spaceAfter=12,
            textColor=colors.HexColor('#2c5282'),
            fontName='Helvetica'
        )
        
        elements.append(Paragraph("FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO", title_style))
        elements.append(Paragraph("FIMLM", subtitle_style))
        elements.append(Paragraph("COMPROBANTE DE SALIDA DE INVENTARIO", subtitle_style))
        
        elements.append(Spacer(1, 0.2*cm))
        elements.append(self._crear_linea_divisoria())
        
        return elements
    
    def _crear_info_salida(self, salida_data):
        """Crea la sección de información de la salida."""
        elements = []
    
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            spaceAfter=3
        )
    
        fecha = salida_data.get('fecha') or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
        info_text = f"""
        <b>FECHA Y HORA:</b> {fecha}<br/>
        <b>DESTINO/RESPONSABLE:</b> {salida_data.get('destino', 'No especificado')}<br/>
        <b>NÚMERO DE REMISIÓN (RM):</b> {salida_data.get('remision', 'N/A')}<br/>
        <b>NÚMERO DE CASO:</b> {salida_data.get('caso', 'N/A')}<br/>
        <b>NÚMERO DE CAJAS:</b> {salida_data.get('numero_cajas', 'N/A')}<br/>
        """
    
        if salida_data.get('kit_nombre'):
            info_text += f"<b>NOMBRE DEL KIT:</b> {salida_data['kit_nombre']}<br/>"
    
        info_text += f"<b>REGISTRADO POR:</b> {salida_data.get('usuario', 'Sistema')}"
    
        elements.append(Paragraph(info_text, info_style))
        return elements
    
    def _crear_tabla_productos(self, productos_data, salida_data):
        """Crea la tabla de productos."""
        elements = []
        
        title_style = ParagraphStyle(
            'TableTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.black
        )
        
        if salida_data.get('kit_nombre'):
            elements.append(Paragraph(f"PRODUCTOS DEL KIT: {salida_data['kit_nombre']}", title_style))
        else:
            elements.append(Paragraph("PRODUCTOS", title_style))
        
        table_data = []
        
        headers = ['No.', 'CÓDIGO', 'DESCRIPCIÓN', 'CANTIDAD']
        if salida_data.get('kit_nombre'):
            headers = ['No.', 'CÓDIGO', 'DESCRIPCIÓN', 'UNID/KIT', 'TOTAL']
        
        table_data.append(headers)
        
        total_general = 0
        for i, producto in enumerate(productos_data, 1):
            row = [
                str(i),
                producto.get('producto_codigo', 'N/A'),
                producto.get('producto_nombre', 'Producto'),
            ]
            
            if salida_data.get('kit_nombre'):
                cantidad_kit = producto.get('cantidad_por_kit', 0)
                cantidad_total = producto.get('cantidad_total', 0)
                row.extend([str(cantidad_kit), str(cantidad_total)])
                total_general += cantidad_total
            else:
                cantidad = producto.get('cantidad', 0)
                row.append(str(cantidad))
                total_general += cantidad
        
            table_data.append(row)
        
        total_row = ['', '', 'TOTAL', str(total_general)]
        if salida_data.get('kit_nombre'):
            total_row = ['', '', 'TOTAL GENERAL', '', str(total_general)]
        
        table_data.append(total_row)
        
        col_widths = [1*cm, 2.5*cm, 9*cm, 2.5*cm]
        if salida_data.get('kit_nombre'):
            col_widths = [1*cm, 2.5*cm, 7*cm, 2*cm, 2*cm]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3d7c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, -1), (-1, -1), 1.5, colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (-1, 1), (-1, -2), 'CENTER'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        return elements
    
    def _crear_observaciones(self, observaciones):
        """Crea la sección de observaciones."""
        elements = []
        
        obs_style = ParagraphStyle(
            'ObservacionesStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            backColor=colors.HexColor('#f8f9fa'),
            borderPadding=8,
            borderWidth=1,
            borderColor=colors.grey,
            borderRadius=3
        )
        
        obs_text = f"""
        <b>OBSERVACIONES / NOTAS ADICIONALES:</b><br/>
        {observaciones}
        """
        
        elements.append(Paragraph(obs_text, obs_style))
        return elements
    
    def _crear_seccion_firmas(self):
        """Crea la sección de firmas."""
        elements = []
        
        title_style = ParagraphStyle(
            'FirmasTitle',
            parent=self.styles['Heading3'],
            fontSize=11,
            spaceAfter=15,
            alignment=1
        )
        
        elements.append(Paragraph("FIRMAS Y SELLOS", title_style))
        
        firmas_data = [
            ['ENTREGADO POR:', 'RECIBIDO POR:'],
            ['', ''],
            ['_________________________', '_________________________'],
            ['Nombre y Apellido', 'Nombre y Apellido'],
            ['', ''],
            ['_________________________', '_________________________'],
            ['C.C./NIT', 'C.C./NIT'],
            ['', ''],
            ['_________________________', '_________________________'],
            ['Firma / Sello', 'Firma / Sello'],
        ]
        
        table = Table(firmas_data, colWidths=[6*cm, 6*cm, 6*cm])
        
        style = TableStyle([
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 3), (-1, 3), 'CENTER'),
            ('ALIGN', (0, 6), (-1, 6), 'CENTER'),
            ('ALIGN', (0, 9), (-1, 9), 'CENTER'),
            ('SPAN', (0, 1), (1, 1)),
            ('SPAN', (0, 4), (1, 4)),
            ('SPAN', (0, 7), (1, 7)),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        return elements
    
    def _crear_pie_pagina(self):
        """Crea el pie de página."""
        elements = []
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=1,
            textColor=colors.grey,
            spaceBefore=10
        )
        
        footer_text = """
        <b>FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO - FIMLM</b><br/>
        Sistema de Gestión de Inventarios • Documento generado automáticamente
        """
        
        elements.append(self._crear_linea_divisoria())
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements
    
    def _crear_linea_divisoria(self):
        """Crea una línea divisoria."""
        from reportlab.platypus.flowables import HRFlowable
        return HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#1a3d7c'),
            spaceBefore=5,
            spaceAfter=5
        )
    
    # ==========================================
    # NUEVOS MÉTODOS PARA COMPROBANTE MÚLTIPLE
    # ==========================================
    
    def generar_comprobante_multiple(self, salidas_data):
        """
        Genera un comprobante de salida múltiple con varias salidas en un solo PDF
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=self.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # 1. ENCABEZADO
        story.extend(self._crear_encabezado())
        story.append(Spacer(1, 0.5*cm))
        
        # 2. RESUMEN GENERAL
        story.extend(self._crear_resumen_multiple(salidas_data))
        story.append(Spacer(1, 0.5*cm))
        
        # 3. TABLA DE SALIDAS
        story.extend(self._crear_tabla_salidas_multiple(salidas_data))
        story.append(Spacer(1, 1*cm))
        
        # 4. FIRMAS
        story.extend(self._crear_seccion_firmas())
        story.append(Spacer(1, 0.5*cm))
        
        # 5. PIE DE PÁGINA
        story.extend(self._crear_pie_pagina())
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _crear_resumen_multiple(self, salidas_data):
        """Crea el resumen de la confirmación múltiple"""
        elements = []
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            spaceAfter=3
        )
        
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        total_salidas = len(salidas_data)
        total_cajas = sum(s.get('cajas', 0) for s in salidas_data)
        
        info_text = f"""
        <b>FECHA Y HORA:</b> {fecha}<br/>
        <b>TOTAL DE SALIDAS CONFIRMADAS:</b> {total_salidas}<br/>
        <b>TOTAL DE CAJAS:</b> {total_cajas}<br/>
        """
        
        elements.append(Paragraph(info_text, info_style))
        return elements
    
    def _crear_tabla_salidas_multiple(self, salidas_data):
        """Crea la tabla con el resumen de todas las salidas"""
        elements = []
        
        for i, salida in enumerate(salidas_data, 1):
            # Título de la salida
            salida_title = ParagraphStyle(
                'SalidaTitle',
                parent=self.styles['Heading4'],
                fontSize=10,
                spaceAfter=5,
                textColor=colors.HexColor('#1a3d7c')
            )
            
            # Nombre de la salida
            nombre_mostrar = salida.get('nombre', 'Salida')
        
            elements.append(Paragraph(f"<b>{i}. {nombre_mostrar}</b>", salida_title))
            
            # Información básica
            info_text = f"""
            <b>RM:</b> {salida.get('remision', 'N/A')} | 
            <b>CASO:</b> {salida.get('caso', 'N/A')} | 
            <b>BENEFICIARIO:</b> {salida.get('cliente', 'No especificado')} | 
            <b>CAJAS:</b> {salida.get('cajas', 0)}
            """
            elements.append(Paragraph(info_text, self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
            
            # Productos
            productos = salida.get('productos', [])
            
            if productos and len(productos) > 0:
               # Mostrar lista de productos (solo nombres)
               productos_text = ", ".join([p.get('producto_nombre', 'N/A') for p in productos])
               elements.append(Paragraph(f"<b>Productos:</b> {productos_text}", self.styles['Normal']))
               elements.append(Spacer(1, 0.3*cm))
            else:
               elements.append(Paragraph("<i>No hay productos registrados</i>", self.styles['Normal']))
            
            # Separador entre salidas
            if i < len(salidas_data):
                elements.append(self._crear_linea_divisoria())
                elements.append(Spacer(1, 0.3*cm))
        
        return elements
    
    def _crear_info_salida_mercado(self, salida_data):
        """Crea la sección de información de la salida para mercado"""
        elements = []
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            spaceAfter=3
        )
        
        fecha = salida_data.get('fecha') or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        info_text = f"""
        <b>REMISIÓN N°:</b> {salida_data.get('remision', 'N/A')}<br/>
        <b>FECHA Y HORA:</b> {fecha}<br/>
        <b>MERCADO:</b> {salida_data.get('nombre_mercado', 'No especificado').replace('_', ' ')}<br/>
        <b>CANTIDAD DE KITS:</b> {salida_data.get('cantidad_kits', 1)}<br/>
        <b>BENEFICIARIO:</b> {salida_data.get('destino', 'No especificado')}<br/>
        <b>REFERENCIA/CASO:</b> {salida_data.get('caso', 'No especificada')}<br/>
        <b>REGISTRADO POR:</b> {salida_data.get('usuario', 'Sistema')}
        """
        
        elements.append(Paragraph(info_text, info_style))
        return elements
    
    def _crear_tabla_productos_mercado(self, productos_data):
        """Crea la tabla de productos para mercado"""
        elements = []
        
        title_style = ParagraphStyle(
            'TableTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.black
        )
        
        elements.append(Paragraph("PRODUCTOS ENTREGADOS", title_style))
        
        table_data = [['No.', 'CÓDIGO', 'DESCRIPCIÓN', 'UBICACIÓN', 'CANTIDAD']]
        
        total_general = 0
        for i, producto in enumerate(productos_data, 1):
            row = [
                str(i),
                producto.get('producto_codigo', 'N/A'),
                producto.get('producto_nombre', 'Producto'),
                producto.get('ubicacion', 'Sin ubicación'),
                str(producto.get('cantidad', 0))
            ]
            table_data.append(row)
            total_general += producto.get('cantidad', 0)
        
        table_data.append(['', '', '', 'TOTAL', str(total_general)])
        
        col_widths = [1*cm, 2.5*cm, 7*cm, 3*cm, 2*cm]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3d7c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, -1), (-1, -1), 1.5, colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (-1, 1), (-1, -2), 'CENTER'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        return elements


# ==========================================
# FUNCIONES FUERA DE LA CLASE
# ==========================================

def generar_pdf_salida_simple(salida_data, productos_data):
    """Función simple para generar PDF de salida."""
    generator = PDFGenerator()
    return generator.generar_comprobante_salida(salida_data, productos_data)


def generar_comprobante_salida_mercado(salida_data, productos_data):
    """Función simple para generar PDF de salida de mercado."""
    generator = PDFGenerator()
    return generator.generar_comprobante_mercado(salida_data, productos_data)