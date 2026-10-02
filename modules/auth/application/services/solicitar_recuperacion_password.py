import secrets
from datetime import UTC, datetime, timedelta

from modules.auth.application.dto.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordInput,
)
from modules.auth.application.ports.email_sender import EmailSenderPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from shared.domain.entities.audit_persona import AuditPersona

EXPIRACION_TOKEN = timedelta(hours=1)


class SolicitarRecuperacionPasswordService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        email_sender: EmailSenderPort,
    ):
        self._usuario_repository = usuario_repository
        self._email_sender = email_sender

    async def ejecutar(self, entrada: SolicitarRecuperacionPasswordInput) -> None:
        """Genera un token de recuperación y envía el email, si el usuario existe.

        No lanza error ni distingue en su resultado si el email está registrado
        o no — la ruta HTTP siempre debe responder el mismo mensaje genérico,
        igual que el legacy, para no revelar cuentas existentes.
        """
        email = entrada.email.strip().lower()
        usuario = await self._usuario_repository.obtener_por_email(email)
        if usuario is None:
            return

        token = secrets.token_urlsafe(32)
        ahora = datetime.now(UTC)
        usuario_con_token = usuario.generar_token_reset(
            token=token,
            expira=ahora + EXPIRACION_TOKEN,
            actualizado_por=AuditPersona(
                id_persona=usuario.id, nombre=usuario.username, fecha=ahora
            ),
        )
        await self._usuario_repository.actualizar(usuario_con_token)
        self._email_sender.enviar_recuperacion_password(email, token)
