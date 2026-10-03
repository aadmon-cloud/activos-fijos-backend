from bson import ObjectId

from modules.solicitudes.application.ports.activo_resumen_port import (
    ActivoResumen,
    ActivoResumenPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "activos" por nombre en vez de importar modules.activos: evita que
# solicitudes dependa del codigo de otro modulo, al costo de conocer el nombre de la coleccion
# y de los campos de referencia (responsable_id, area_id).
_NOMBRE_COLECCION_ACTIVOS = "activos"


class MongoActivoResumenAdapter(ActivoResumenPort):
    async def obtener_resumen(self, activo_id: str) -> ActivoResumen | None:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]
        doc = await coleccion.find_one({"_id": ObjectId(activo_id)})
        if doc is None:
            return None
        return ActivoResumen(
            id=str(doc["_id"]),
            responsable_id=str(doc["responsable_id"]),
            area_id=str(doc["area_id"]),
        )
