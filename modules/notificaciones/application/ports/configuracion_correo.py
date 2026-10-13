from abc import ABC, abstractmethod


class ConfiguracionCorreoPort(ABC):
    @abstractmethod
    def esta_configurado(self) -> bool:
        """Si hay lo necesario para enviar correos reales."""

    @abstractmethod
    def url_aplicacion(self) -> str | None:
        """Direccion publica del frontend, para los enlaces de los correos."""

    @abstractmethod
    def remitente(self) -> str | None:
        """Direccion desde la que se envia, o None si no hay."""
