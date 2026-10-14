import os

os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("ENTORNO", "local")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")


import pytest  # noqa: E402

from shared.infrastructure.security.consulta_permisos_rol_mongo import (  # noqa: E402
    ConsultaPermisosRolMongo,
    consulta_permisos_rol,
)


@pytest.fixture(autouse=True)
def _permisos_de_fabrica(monkeypatch):
    """Sin Mongo en las pruebas, cada rol tiene la matriz de fabrica (la de antes de la administracion de permisos).

    Una prueba que necesite otra matriz sustituye `_leer_documento` por su propia version.
    """

    async def _sin_documento(self, rol):
        return None

    monkeypatch.setattr(ConsultaPermisosRolMongo, "_leer_documento", _sin_documento)
    consulta_permisos_rol.invalidar()
