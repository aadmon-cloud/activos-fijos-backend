import os

from pymongo import MongoClient
from pymongo.database import Database


def conectar_legacy() -> tuple[MongoClient, Database]:
    url = os.environ.get("LEGACY_MONGO_URL", "mongodb://localhost:27017")
    nombre_db = os.environ.get("LEGACY_MONGO_DB", "GESTIONACTIVOSFIJOS")
    cliente = MongoClient(url)
    return cliente, cliente[nombre_db]
