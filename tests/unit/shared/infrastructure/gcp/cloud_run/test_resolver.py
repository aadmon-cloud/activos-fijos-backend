from unittest.mock import patch

import pytest

from shared.application.service_invocation.exceptions import (
    ErrorServicioExternoNoConfigurado,
)
from shared.infrastructure.gcp.cloud_run.resolver import ResolutorServicioCloudRun


def test_resolver_usa_url_directa_de_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("CLOUD_RUN_FACTURACION_URL", "https://facturacion.example.com")

    resolutor = ResolutorServicioCloudRun("mi-proyecto")
    config = resolutor.resolver("facturacion")

    assert config.url_base == "https://facturacion.example.com"


@patch("shared.infrastructure.gcp.cloud_run.resolver.GestorSecretosGCP")
def test_resolver_usa_secret_manager_y_cachea_el_resultado(gestor_mock_cls, monkeypatch):
    monkeypatch.setenv(
        "CLOUD_RUN_FACTURACION_URL_SECRET_NAME", "url-facturacion"
    )
    gestor_mock_cls.return_value.obtener_secreto.return_value = "https://facturacion.example.com"

    resolutor = ResolutorServicioCloudRun("mi-proyecto")
    config_1 = resolutor.resolver("facturacion")
    config_2 = resolutor.resolver("facturacion")

    assert config_1.url_base == "https://facturacion.example.com"
    assert config_2.url_base == "https://facturacion.example.com"
    gestor_mock_cls.return_value.obtener_secreto.assert_called_once()


def test_resolver_lanza_error_si_no_esta_configurado():
    resolutor = ResolutorServicioCloudRun("mi-proyecto")

    with pytest.raises(ErrorServicioExternoNoConfigurado):
        resolutor.resolver("servicio-inexistente")
