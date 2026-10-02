from abc import ABC, abstractmethod


class EmailSenderPort(ABC):
    @abstractmethod
    def enviar_recuperacion_password(self, email: str, token: str) -> bool:
        """Envía el email de recuperación de password.

        Retorna False si no se pudo enviar (p. ej. SMTP no configurado o error
        de entrega) en vez de lanzar una excepción — el flujo de "olvidé mi
        password" no debe fallar por un problema de email (ver la regla de no
        revelar si el email existe, en SolicitarRecuperacionPasswordService).
        """
