from unittest.mock import MagicMock, patch

from shared.application.notifications.ports import AdjuntoCorreo
from shared.infrastructure.notifications.smtp_notificador import SMTPNotificador

_RUTA_SETTINGS = "shared.infrastructure.notifications.smtp_notificador.settings"


def _settings_mock(**overrides):
    settings_mock = MagicMock()
    settings_mock.ENTORNO = "local"
    settings_mock.SMTP_HOST = "smtp.example.com"
    settings_mock.SMTP_PORT = 587
    settings_mock.SMTP_USER = "usuario@example.com"
    settings_mock.SMTP_PASSWORD = "clave-local"
    settings_mock.SMTP_PASSWORD_SECRET_NAME = None
    settings_mock.SMTP_FROM_EMAIL = "no-responder@example.com"
    settings_mock.SMTP_FROM_NAME = "Sistema de Activos Fijos"
    settings_mock.SMTP_USE_TLS = True
    for clave, valor in overrides.items():
        setattr(settings_mock, clave, valor)
    return settings_mock


async def test_enviar_arma_el_mensaje_con_adjunto_y_usa_tls_y_login():
    servidor_mock = MagicMock()
    servidor_mock.__enter__.return_value = servidor_mock

    with (
        patch(_RUTA_SETTINGS, _settings_mock()),
        patch(
            "shared.infrastructure.notifications.smtp_notificador.smtplib.SMTP",
            return_value=servidor_mock,
        ) as smtp_cls_mock,
    ):
        await SMTPNotificador().enviar(
            destinatarios=["camilo@x.com", "admin@x.com"],
            asunto="Auditoria de activos",
            cuerpo="Cuerpo del correo",
            adjuntos=[
                AdjuntoCorreo(nombre="auditoria.pdf", contenido=b"%PDF-1.4", tipo_mime="application/pdf")
            ],
        )

    smtp_cls_mock.assert_called_once_with("smtp.example.com", 587, timeout=15)
    servidor_mock.starttls.assert_called_once()
    servidor_mock.login.assert_called_once_with("usuario@example.com", "clave-local")
    servidor_mock.send_message.assert_called_once()

    mensaje_enviado = servidor_mock.send_message.call_args.args[0]
    assert mensaje_enviado["Subject"] == "Auditoria de activos"
    assert mensaje_enviado["To"] == "camilo@x.com, admin@x.com"
    assert "no-responder@example.com" in mensaje_enviado["From"]

    adjuntos = list(mensaje_enviado.iter_attachments())
    assert len(adjuntos) == 1
    assert adjuntos[0].get_filename() == "auditoria.pdf"
    assert adjuntos[0].get_content() == b"%PDF-1.4"


async def test_enviar_sin_tls_no_llama_starttls():
    servidor_mock = MagicMock()
    servidor_mock.__enter__.return_value = servidor_mock

    with (
        patch(_RUTA_SETTINGS, _settings_mock(SMTP_USE_TLS=False)),
        patch(
            "shared.infrastructure.notifications.smtp_notificador.smtplib.SMTP",
            return_value=servidor_mock,
        ),
    ):
        await SMTPNotificador().enviar(
            destinatarios=["camilo@x.com"], asunto="Asunto", cuerpo="Cuerpo", adjuntos=[]
        )

    servidor_mock.starttls.assert_not_called()


async def test_obtener_password_usa_secret_manager_fuera_de_local():
    with (
        patch(
            _RUTA_SETTINGS,
            _settings_mock(
                ENTORNO="produccion",
                SMTP_PASSWORD_SECRET_NAME="smtp-password",
                GCP_PROJECT_ID="mi-proyecto",
            ),
        ),
        patch(
            "shared.infrastructure.notifications.smtp_notificador.GestorSecretosGCP"
        ) as gestor_cls_mock,
    ):
        gestor_cls_mock.return_value.obtener_secreto.return_value = "clave-del-secret-manager"

        notificador = SMTPNotificador()
        password = notificador._obtener_password()
        password_cacheada = notificador._obtener_password()

    assert password == "clave-del-secret-manager"
    assert password_cacheada == "clave-del-secret-manager"
    gestor_cls_mock.return_value.obtener_secreto.assert_called_once_with("smtp-password")
