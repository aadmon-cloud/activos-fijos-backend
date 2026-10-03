from bson import ObjectId

from modules.usuarios.application.ports.verificador_area import VerificadorAreaPort
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "areas" de catalogos por nombre en vez de importar modules.catalogos:
# evita que usuarios dependa del codigo de otro modulo, al costo de conocer el nombre de la
# coleccion.
_NOMBRE_COLECCION_AREAS = "areas"


class MongoVerificadorArea(VerificadorAreaPort):
    async def existe(self, area_id: str) -> bool:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_AREAS]
        return await coleccion.find_one({"_id": ObjectId(area_id)}) is not None
