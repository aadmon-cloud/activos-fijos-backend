from bson import ObjectId

from modules.auditorias.application.ports.historial_activo_nota_port import (
    HistorialActivoNotaPort,
)
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Misma coleccion que usa modules.activos (activos_historial), escrita por nombre en vez de
# importar su codigo. El documento tiene la misma forma que espera
# modules.activos.infrastructure.persistence.mongo.historial_activo_repository._doc_a_entidad
# para la variante tipo="nota" de EntradaHistorialActivo.
_NOMBRE_COLECCION_HISTORIAL = "activos_historial"


class MongoHistorialActivoNotaAdapter(HistorialActivoNotaPort):
    async def registrar_nota(
        self, activo_id: str, nota: str, auditoria_id: str, auditor: AuditPersona
    ) -> None:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_HISTORIAL]
        await coleccion.insert_one(
            {
                "activo_id": ObjectId(activo_id),
                "tipo": "nota",
                "nota": nota,
                "auditoria_id": ObjectId(auditoria_id),
                "modificado_por": {
                    "id_persona": auditor.id_persona,
                    "nombre": auditor.nombre,
                    "fecha": auditor.fecha,
                },
            }
        )
