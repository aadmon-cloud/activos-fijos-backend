import logging
from typing import Any
from urllib.parse import urljoin

import google.auth.exceptions
import requests

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)
from shared.application.service_invocation.exceptions import (
    ErrorAutenticacionServicioExterno,
    ErrorInvocacionServicioExterno,
)
from shared.application.service_invocation.ports import (
    IInvocadorServicio,
    IProveedorTokenServicio,
    IResolutorServicioExterno,
)

logger = logging.getLogger(__name__)


class ClienteCloudRun(IInvocadorServicio):
    def __init__(
        self,
        resolutor: IResolutorServicioExterno,
        proveedor_token: IProveedorTokenServicio,
        nombre_sistema: str | None = None,
        correo_debug: str | None = None,
        sesion: requests.Session | None = None,
    ):
        self._resolutor = resolutor
        self._proveedor_token = proveedor_token
        self._nombre_sistema = nombre_sistema
        self._correo_debug = correo_debug
        self._sesion = sesion or requests.Session()

    def invocar(self, nombre_servicio: str, solicitud: SolicitudServicioExterno) -> Any:
        configuracion_servicio = self._resolutor.resolver(nombre_servicio)
        url = self._construir_url(configuracion_servicio.url_base, solicitud.ruta)
        cabeceras = self._construir_cabeceras(
            nombre_servicio,
            configuracion_servicio,
            solicitud.cabeceras,
        )
        tiempo_espera = (
            solicitud.tiempo_espera_segundos
            or configuracion_servicio.tiempo_espera_segundos
        )

        try:
            respuesta = self._sesion.request(
                method=solicitud.metodo,
                url=url,
                headers=cabeceras,
                json=solicitud.cuerpo_json,
                params=solicitud.parametros_query,
                timeout=tiempo_espera,
            )
        except requests.RequestException as exc:
            raise ErrorInvocacionServicioExterno(
                nombre_servicio=nombre_servicio,
                detalle=str(exc),
            ) from exc

        if not respuesta.ok:
            raise ErrorInvocacionServicioExterno(
                nombre_servicio=nombre_servicio,
                detalle=self._extraer_detalle_error(respuesta),
                status_code=respuesta.status_code,
            )

        return self._parsear_respuesta(respuesta)

    def _construir_cabeceras(
        self,
        nombre_servicio: str,
        configuracion_servicio: ConfiguracionServicioExterno,
        cabeceras_solicitud: dict[str, str],
    ) -> dict[str, str]:
        cabeceras = dict(configuracion_servicio.cabeceras_extra)

        if configuracion_servicio.requiere_autenticacion:
            try:
                token = self._proveedor_token.obtener_token(
                    configuracion_servicio.audiencia_resuelta
                )
            except google.auth.exceptions.GoogleAuthError as exc:
                raise ErrorAutenticacionServicioExterno(
                    nombre_servicio,
                    str(exc),
                ) from exc

            cabeceras["Authorization"] = f"Bearer {token}"

        if self._nombre_sistema:
            cabeceras["X-Sistema"] = self._nombre_sistema

        if self._correo_debug:
            cabeceras["X-Debug-Email"] = self._correo_debug

        cabeceras.update(cabeceras_solicitud)
        return {llave: valor for llave, valor in cabeceras.items() if valor}

    @staticmethod
    def _construir_url(url_base: str, ruta: str) -> str:
        url_base_normalizada = f"{url_base.rstrip('/')}/"
        ruta_normalizada = ruta.lstrip("/")
        return urljoin(url_base_normalizada, ruta_normalizada)

    @staticmethod
    def _extraer_detalle_error(respuesta: requests.Response) -> Any:
        try:
            carga_error = respuesta.json()
        except ValueError:
            return respuesta.text

        if isinstance(carga_error, dict):
            return (
                carga_error.get("detail")
                or carga_error.get("message")
                or carga_error.get("error")
                or respuesta.text
            )
        return str(carga_error)

    @staticmethod
    def _parsear_respuesta(respuesta: requests.Response) -> Any:
        if respuesta.status_code == 204 or not respuesta.content:
            return None

        try:
            return respuesta.json()
        except ValueError:
            return respuesta.text
