from datetime import UTC, datetime

from bson import ObjectId

from modules.activos.application.dto.actualizar_activo_dto import ActualizarActivoDTO
from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.application.services.actualizar_activo import ActualizarActivoService
from modules.activos.application.services.cambiar_estado_activo import CambiarEstadoActivoService
from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    MongoActivoRepository,
)
from modules.activos.infrastructure.persistence.mongo.historial_activo_repository import (
    MongoHistorialActivoRepository,
)
from modules.movimientos.application.ports.activo_movimiento_port import (
    ActivoMovimientoPort,
    ActivoResumenMovimiento,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Unico archivo de movimientos que usa codigo del modulo activos: reutiliza sus servicios reales
# (mismo patron que ActivoEstadoAdapter de solicitudes) para que la matriz de transiciones y el
# historial de activos tengan una sola implementacion, en vez de repetirlos aqui.
_NOMBRE_COLECCION_ACTIVOS = "activos"

# Misma coleccion que usa modules.activos para su historial (escrita por nombre, como lo hace el modulo de
# auditorias): una nota es una entrada `tipo="nota"` sin campo ni valores.
_NOMBRE_COLECCION_HISTORIAL = "activos_historial"


def _resumen(doc: dict) -> ActivoResumenMovimiento:
    return ActivoResumenMovimiento(
        id=str(doc["_id"]),
        responsable_id=str(doc["responsable_id"]),
        estado_ciclo_vida=doc["estado_ciclo_vida"],
        nombre=doc.get("nombre", ""),
        numero_inventario=doc.get("numero_inventario", ""),
    )


class MongoActivoMovimientoAdapter(ActivoMovimientoPort):
    def __init__(self):
        self._activo_repository = MongoActivoRepository()
        self._historial_repository = MongoHistorialActivoRepository()
        self._actualizar_activo = ActualizarActivoService(
            self._activo_repository, self._historial_repository
        )
        self._cambiar_estado_activo = CambiarEstadoActivoService(
            self._activo_repository, self._historial_repository
        )

    async def obtener_resumen(self, activo_id: str) -> ActivoResumenMovimiento | None:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]
        doc = await coleccion.find_one({"_id": ObjectId(activo_id)})

        return _resumen(doc) if doc else None

    async def obtener_resumenes(self, activo_ids: list[str]) -> dict[str, ActivoResumenMovimiento]:
        if not activo_ids:
            return {}

        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]
        documentos = await coleccion.find({"_id": {"$in": [ObjectId(a) for a in activo_ids]}}).to_list(
            length=None
        )

        return {str(doc["_id"]): _resumen(doc) for doc in documentos}

    async def listar_ids_por_responsable(self, responsable_id: str) -> list[str]:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]
        documentos = await coleccion.find({"responsable_id": ObjectId(responsable_id)}, {"_id": 1}).to_list(
            length=None
        )

        return [str(documento["_id"]) for documento in documentos]

    async def cambiar_responsable(
        self, activo_id: str, responsable_nuevo_id: str, actor_id: str, actor_nombre: str
    ) -> bool:
        try:
            await self._actualizar_activo.ejecutar(
                ActualizarActivoDTO(
                    id_activo=activo_id,
                    responsable_id=responsable_nuevo_id,
                    actualizado_por_id=actor_id,
                    actualizado_por_nombre=actor_nombre,
                )
            )
        except ActivoNoEncontradoError:
            return False

        return True

    async def cambiar_estado(
        self, activo_id: str, estado_nuevo: str, actor_id: str, actor_nombre: str
    ) -> bool:
        try:
            await self._cambiar_estado_activo.ejecutar(
                CambiarEstadoActivoDTO(
                    id_activo=activo_id,
                    estado_nuevo=EstadoCicloVida(estado_nuevo),
                    actualizado_por_id=actor_id,
                    actualizado_por_nombre=actor_nombre,
                )
            )
        except (ActivoNoEncontradoError, TransicionEstadoInvalidaError):
            return False

        return True

    async def registrar_nota(
        self, activo_id: str, nota: str, movimiento_id: str, actor_id: str, actor_nombre: str
    ) -> None:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_HISTORIAL]
        await coleccion.insert_one(
            {
                "activo_id": ObjectId(activo_id),
                "tipo": "nota",
                "nota": nota,
                "movimiento_id": ObjectId(movimiento_id),
                "modificado_por": {
                    "id_persona": actor_id,
                    "nombre": actor_nombre,
                    "fecha": datetime.now(UTC),
                },
            }
        )
