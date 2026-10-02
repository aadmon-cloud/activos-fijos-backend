# app/utils/codigos.py
import random
import string
from datetime import datetime
import qrcode
import barcode
from barcode.writer import ImageWriter
import io
import base64
from typing import Optional
from PIL import Image, ImageDraw

def generar_codigo_producto(prefix: str = "PROD") -> str:
    """
    Genera un código único para productos.
    Formato: PREFIJO-YYYYMMDD-XXXXXX
    """
    fecha = datetime.now().strftime("%Y%m%d")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{fecha}-{random_chars}"

def generar_codigo_barras(codigo: str) -> str:
    """
    Genera imagen de código de barras en base64.
    """
    try:
        # Usar Code128 que acepta cualquier texto
        code128 = barcode.get_barcode_class('code128')
        
        # Configuración del writer
        writer_options = {
            'write_text': False,
            'quiet_zone': 2.0,
            'module_height': 10.0,
            'module_width': 0.3,
            'font_size': 10,
        }
        
        barcode_img = code128(codigo, writer=ImageWriter())
        
        # Guardar en buffer
        buffer = io.BytesIO()
        barcode_img.write(buffer, options=writer_options)
        buffer.seek(0)
        
        # Convertir a base64
        b64_string = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64_string}"
        
    except Exception as e:
        print(f"Error generando código de barras: {e}")
        return ""

def generar_qr_code(codigo: str, data_extra: Optional[dict] = None) -> str:
    """
    Genera código QR en base64.
    """
    try:
        # Datos para el QR
        qr_data = {
            "codigo": codigo,
            "sistema": "Inventario FIMLM",
            "timestamp": datetime.now().isoformat(),
            "url": f"/productos/{codigo}"
        }
        
        if data_extra:
            qr_data.update(data_extra)
        
        # Crear QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Crear imagen
        img = qr.make_image(fill_color="#1e40af", back_color="#f8fafc")
        
        # Opcional: agregar logo
        img = agregar_logo_qr(img)
        
        # Guardar en buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        # Convertir a base64
        b64_string = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64_string}"
        
    except Exception as e:
        print(f"Error generando QR: {e}")
        return ""

def agregar_logo_qr(img_qr):
    """
    Agrega un logo simple al centro del QR.
    """
    try:
        # Tamaño del logo (10% del tamaño del QR)
        qr_size = img_qr.size[0]
        logo_size = qr_size // 10
        
        # Crear logo simple
        logo = Image.new('RGB', (logo_size, logo_size), color='white')
        draw = ImageDraw.Draw(logo)
        
        # Dibujar cuadrado azul
        margin = 2
        draw.rectangle(
            [margin, margin, logo_size-margin, logo_size-margin],
            fill='#2563eb',
            outline='#1d4ed8',
            width=1
        )
        
        # Dibujar "I" blanca
        try:
            from PIL import ImageFont
            font_size = logo_size - 10
            draw.text(
                (logo_size//2, logo_size//2),
                "I",
                fill='white',
                anchor='mm',
                font_size=font_size
            )
        except:
            # Si no hay fuente, dibujar punto
            draw.ellipse(
                [logo_size//2-2, logo_size//2-2, logo_size//2+2, logo_size//2+2],
                fill='white'
            )
        
        # Pegar logo en el centro del QR
        pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
        img_qr.paste(logo, pos)
        
        return img_qr
        
    except Exception as e:
        print(f"No se pudo agregar logo: {e}")
        return img_qr

def validar_formato_codigo(codigo: str) -> dict:
    """
    Valida y determina el tipo de código.
    """
    codigo = str(codigo).strip()
    
    # Código de producto interno
    if codigo.startswith('PROD-') and len(codigo) == 20:
        return {"valido": True, "tipo": "producto_interno"}
    
    # EAN-13 (13 dígitos)
    if codigo.isdigit() and len(codigo) == 13:
        return {"valido": True, "tipo": "ean13"}
    
    # UPC (12 dígitos)
    if codigo.isdigit() and len(codigo) == 12:
        return {"valido": True, "tipo": "upc"}
    
    # Código de barras genérico
    if 8 <= len(codigo) <= 20 and all(c.isalnum() for c in codigo):
        return {"valido": True, "tipo": "codigo_barras"}
    
    return {"valido": False, "tipo": "desconocido"}