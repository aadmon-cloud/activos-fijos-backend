from abc import ABC, abstractmethod
from typing import Any

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)


class IInvocadorServicio(ABC):
    @abstractmethod
    def invocar(self, nombre_servicio: str, solicitud: SolicitudServicioExterno) -> Any: ...


class IResolutorServicioExterno(ABC):
    @abstractmethod
    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno: ...


class IProveedorTokenServicio(ABC):
    @abstractmethod
    def obtener_token(self, audiencia: str) -> str: ...
