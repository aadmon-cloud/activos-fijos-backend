from modules.mantenimientos.application.ports.buscador_activos_port import BuscadorActivosPort
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "activos" por nombre en vez de importar modules.activos.
_NOMBRE_COLECCION_ACTIVOS = "activos"


class MongoBuscadorActivos(BuscadorActivosPort):
    async def buscar_por_codigo(self, codigos: list[str]) -> dict[str, str]:
        if not codigos:
            return {}

        documentos = await mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS].find(
            {"numero_inventario": {"$in": codigos}}, {"numero_inventario": 1}
        ).to_list(length=None)

        return {documento["numero_inventario"]: str(documento["_id"]) for documento in documentos}
