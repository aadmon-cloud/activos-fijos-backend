# app/core/email.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Configuración de Gmail (usar variables de entorno)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")  # Tu correo de Gmail
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Contraseña de aplicación de Gmail
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """
    Enviar correo electrónico usando Gmail SMTP
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️ Email no configurado. Configura SMTP_USER y SMTP_PASSWORD en .env")
        return False
    
    try:
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        # Versión texto plano
        part_text = MIMEText(body, 'plain')
        msg.attach(part_text)
        
        # Versión HTML (si se proporciona)
        if html_body:
            part_html = MIMEText(html_body, 'html')
            msg.attach(part_html)
        
        # Enviar email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email enviado a {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False

def send_password_reset_email(to_email: str, token: str) -> bool:
    """
    Enviar email de recuperación de contraseña
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    subject = "Recuperación de contraseña - Inventario FIMLM"
    
    body = f"""
    Hola,
    
    Has solicitado restablecer tu contraseña.
    
    Haz clic en el siguiente enlace para crear una nueva contraseña:
    {reset_link}
    
    Este enlace es válido por 1 hora.
    
    Si no solicitaste este cambio, ignora este mensaje.
    
    Saludos,
    Equipo de Inventario FIMLM
    """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Recuperación de contraseña</h2>
        <p>Has solicitado restablecer tu contraseña.</p>
        <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
        <p><a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer contraseña</a></p>
        <p>O copia este enlace en tu navegador: <br/><a href="{reset_link}">{reset_link}</a></p>
        <p>Este enlace es válido por <strong>1 hora</strong>.</p>
        <p>Si no solicitaste este cambio, ignora este mensaje.</p>
        <br/>
        <p>Saludos,<br/>Equipo de Inventario FIMLM</p>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, body, html_body)

def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Enviar email de bienvenida al registrar usuario
    """
    subject = "Bienvenido a Inventario FIMLM"
    
    body = f"""
    Hola {username},
    
    Bienvenido al Sistema de Inventario FIMLM.
    
    Tu cuenta ha sido creada exitosamente.
    
    Saludos,
    Equipo de Inventario FIMLM
    """
    
    return send_email(to_email, subject, body)