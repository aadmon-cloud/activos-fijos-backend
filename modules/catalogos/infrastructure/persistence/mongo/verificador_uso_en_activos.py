from bson import ObjectId

from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "activos" por nombre en vez de importar modules.activos: evita que
# catalogos dependa del codigo de otro modulo, al costo de conocer el nombre de la coleccion
# y de los campos de referencia (area_id, categoria_id, condicion_id, lugar_id).
_NOMBRE_COLECCION_ACTIVOS = "activos"


class MongoVerificadorUsoEnActivos(VerificadorUsoEnActivosPort):
    @property
    def _collection(self):
        return mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]

    async def area_esta_en_uso(self, area_id: str) -> bool:
        return await self._collection.find_one({"area_id": ObjectId(area_id)}) is not None

    async def categoria_esta_en_uso(self, categoria_id: str) -> bool:
        return (
            await self._collection.find_one({"categoria_id": ObjectId(categoria_id)})
            is not None
        )

    async def condicion_esta_en_uso(self, condicion_id: str) -> bool:
        return (
            await self._collection.find_one({"condicion_id": ObjectId(condicion_id)})
            is not None
        )

    async def lugar_esta_en_uso(self, lugar_id: str) -> bool:
        return await self._collection.find_one({"lugar_id": ObjectId(lugar_id)}) is not None
