import os
from unittest.mock import MagicMock, patch

from shared.infrastructure.persistence.mongo.database import DatabaseManager


@patch("shared.infrastructure.persistence.mongo.database.AsyncIOMotorClient")
def test_connect_en_modo_local_no_usa_tls_ni_secret_manager(cliente_mock_cls, monkeypatch):
    monkeypatch.setenv("ENTORNO", "local")
    from config.settings import Settings

    with patch("shared.infrastructure.persistence.mongo.database.settings", Settings()):
        manager = DatabaseManager()
        manager.connect()

    _, kwargs = cliente_mock_cls.call_args
    assert "tls" not in kwargs
    assert "tlsCertificateKeyFile" not in kwargs
    manager.close()


@patch("shared.infrastructure.persistence.mongo.database.AsyncIOMotorClient")
@patch("shared.infrastructure.persistence.mongo.database.GestorSecretosGCP")
def test_connect_en_modo_cloud_usa_certificado_de_secret_manager(
    gestor_mock_cls, cliente_mock_cls, monkeypatch
):
    monkeypatch.setenv("ENTORNO", "cloud")
    monkeypatch.setenv("MONGO_CERT_SECRET_NAME", "cert-mongo")
    from config.settings import Settings

    gestor_mock_cls.return_value.obtener_secreto.return_value = "contenido-certificado"

    with patch(
        "shared.infrastructure.persistence.mongo.database.settings",
        Settings(),
    ):
        manager = DatabaseManager()
        manager.connect()

        _, kwargs = cliente_mock_cls.call_args
        assert kwargs["tls"] is True
        assert kwargs["authMechanism"] == "MONGODB-X509"
        assert os.path.exists(kwargs["tlsCertificateKeyFile"])

        manager.close()

    assert manager.client is None


def test_connect_es_idempotente_si_ya_hay_cliente():
    manager = DatabaseManager()
    cliente_falso = MagicMock()
    manager.client = cliente_falso

    manager.connect()

    assert manager.client is cliente_falso
