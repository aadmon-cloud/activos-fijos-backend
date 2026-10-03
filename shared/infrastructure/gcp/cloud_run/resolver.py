import os

from shared.application.service_invocation.dto import ConfiguracionServicioExterno
from shared.application.service_invocation.exceptions import (
    ErrorServicioExternoNoConfigurado,
)
from shared.application.service_invocation.ports import IResolutorServicioExterno
from shared.infrastructure.gcp.secret_manager import GestorSecretosGCP


class ResolutorServicioCloudRun(IResolutorServicioExterno):
    def __init__(self, id_proyecto: str):
        self._id_proyecto = id_proyecto
        self._gestor_secretos: GestorSecretosGCP | None = None
        self._cache: dict[str, ConfiguracionServicioExterno] = {}

    @property
    def _gestor(self) -> GestorSecretosGCP:
        if self._gestor_secretos is None:
            self._gestor_secretos = GestorSecretosGCP(self._id_proyecto)
        return self._gestor_secretos

    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno:
        nombre_normalizado = self._normalizar_nombre_servicio(nombre_servicio)

        if nombre_normalizado in self._cache:
            return self._cache[nombre_normalizado]

        url_base = self._resolver_url_directa(nombre_normalizado)
        if not url_base:
            nombre_secreto = self._resolver_nombre_secreto(nombre_normalizado)
            if nombre_secreto:
                url_base = self._gestor.obtener_secreto(nombre_secreto)

        if not url_base:
            raise ErrorServicioExternoNoConfigurado(nombre_servicio)

        configuracion = ConfiguracionServicioExterno(
            nombre=nombre_servicio,
            url_base=url_base.rstrip("/"),
        )
        self._cache[nombre_normalizado] = configuracion
        return configuracion

    @staticmethod
    def _normalizar_nombre_servicio(nombre_servicio: str) -> str:
        return nombre_servicio.strip().upper().replace("-", "_")

    @staticmethod
    def _resolver_url_directa(nombre_normalizado: str) -> str | None:
        variables_entorno = [
            f"CLOUD_RUN_{nombre_normalizado}_URL",
            f"CLOUD_RUN_URL_{nombre_normalizado}",
        ]
        for variable_entorno in variables_entorno:
            valor = os.getenv(variable_entorno)
            if valor:
                return valor
        return None

    @staticmethod
    def _resolver_nombre_secreto(nombre_normalizado: str) -> str | None:
        variables_entorno = [
            f"CLOUD_RUN_{nombre_normalizado}_URL_SECRET_NAME",
            f"CLOUD_RUN_URL_{nombre_normalizado}_NAME",
        ]
        for variable_entorno in variables_entorno:
            valor = os.getenv(variable_entorno)
            if valor:
                return valor
        return None
