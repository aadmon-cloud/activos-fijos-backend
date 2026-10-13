from modules.dashboard.application.ports.activos_resumen_port import ActivosResumenPort
from modules.dashboard.domain.entities import ResumenActivos
from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "activos"


class MongoActivosResumenAdapter(ActivosResumenPort):
    async def obtener(self) -> ResumenActivos:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
        total, agrupados = await contar_y_agrupar(coleccion, "estado_ciclo_vida", "tipo")

        return ResumenActivos(
            total=total,
            por_estado_ciclo_vida=agrupados["estado_ciclo_vida"],
            por_tipo=agrupados["tipo"],
        )
