from modules.dashboard.application.ports.auditorias_resumen_port import AuditoriasResumenPort
from modules.dashboard.domain.entities import AuditoriaReciente, ResumenAuditorias
from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_AUDITORIAS = "auditorias"
_NOMBRE_COLECCION_USUARIOS = "usuarios"
_RESULTADO_NO_ENCONTRADO = "no_encontrado"


class MongoAuditoriasResumenAdapter(AuditoriasResumenPort):
    async def obtener(self, limite_recientes: int) -> ResumenAuditorias:
        db = mongo_manager.get_database()
        coleccion = db[_NOMBRE_COLECCION_AUDITORIAS]
        total, agrupados = await contar_y_agrupar(coleccion, "estado")

        documentos = await coleccion.aggregate(
            [
                {"$sort": {"_id": -1}},
                {"$limit": limite_recientes},
                {
                    "$project": {
                        "usuario_auditado_id": 1,
                        "fecha_cierre": 1,
                        "no_encontrados": {
                            "$size": {
                                "$filter": {
                                    "input": "$items",
                                    "cond": {"$eq": ["$$this.resultado", _RESULTADO_NO_ENCONTRADO]},
                                }
                            }
                        },
                    }
                },
            ]
        ).to_list(length=limite_recientes)

        nombres = await self._resolver_nombres(db, [doc["usuario_auditado_id"] for doc in documentos])

        ultimas = [
            AuditoriaReciente(
                id=str(doc["_id"]),
                usuario_auditado_id=str(doc["usuario_auditado_id"]),
                usuario_auditado_nombre=nombres.get(doc["usuario_auditado_id"]),
                fecha_cierre=doc.get("fecha_cierre"),
                no_encontrados=doc["no_encontrados"],
            )
            for doc in documentos
        ]

        return ResumenAuditorias(total=total, por_estado=agrupados["estado"], ultimas=ultimas)

    async def _resolver_nombres(self, db, usuario_ids: list) -> dict:
        if not usuario_ids:
            return {}

        nombres = {}
        async for doc in db[_NOMBRE_COLECCION_USUARIOS].find(
            {"_id": {"$in": usuario_ids}}, {"nombre": 1, "apellido": 1}
        ):
            nombres[doc["_id"]] = f"{doc['nombre']} {doc['apellido']}".strip()
        return nombres
