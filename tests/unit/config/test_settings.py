from config.settings import Settings


def test_settings_usa_valores_por_defecto_cuando_no_se_especifican():
    settings = Settings(
        GCP_PROJECT_ID="proyecto-x",
        MONGO_URL="mongodb://localhost:27017",
        MONGO_DB="mi_db",
    )
    assert settings.ENTORNO == "local"
    assert settings.MONGO_CERT_SECRET_NAME is None
    assert settings.GOOGLE_CLOUD_RUN_AUDIENCE is None


def test_settings_lee_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proyecto-y")
    monkeypatch.setenv("MONGO_URL", "mongodb://otra:27017")
    monkeypatch.setenv("MONGO_DB", "otra_db")
    monkeypatch.setenv("ENTORNO", "cloud")

    settings = Settings()

    assert settings.GCP_PROJECT_ID == "proyecto-y"
    assert settings.ENTORNO == "cloud"
