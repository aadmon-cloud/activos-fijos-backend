from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.infrastructure.persistence.mongo.pipelines.movimiento_pendiente_pipeline import (
    MovimientoPendientePipelineBuilder,
)
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "movimientos_pendientes"


class MongoMovimientoPendienteRepository(MovimientoPendienteRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def crear(
        self, pendiente: MovimientoPendiente, uow: UnitOfWorkPort | None = None
    ) -> MovimientoPendiente:
        session = uow.session if uow else None
        nuevo_id = ObjectId()
        pendiente_con_id = pendiente.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(pendiente_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc, session=session)
        return pendiente_con_id

    async def obtener_por_id(self, movimiento_pendiente_id: str) -> MovimientoPendiente | None:
        doc = await self._col.find_one({"_id": ObjectId(movimiento_pendiente_id)})
        return self._doc_a_entidad(doc) if doc else None

    async def actualizar(
        self, pendiente: MovimientoPendiente, uow: UnitOfWorkPort | None = None
    ) -> MovimientoPendiente:
        session = uow.session if uow else None
        doc = self._entidad_a_doc(pendiente)
        await self._col.replace_one({"_id": ObjectId(pendiente.id)}, doc, session=session)
        return pendiente

    async def eliminar(
        self, movimiento_pendiente_id: str, uow: UnitOfWorkPort | None = None
    ) -> None:
        session = uow.session if uow else None
        await self._col.delete_one(
            {"_id": ObjectId(movimiento_pendiente_id)}, session=session
        )

    async def listar(
        self, filtro: ListarMovimientosPendientesInput
    ) -> tuple[list[MovimientoPendiente], int]:
        match = _filtro_a_match(filtro)
        pipeline = (
            MovimientoPendientePipelineBuilder()
            .filtrar(match)
            .ordenar_por_fecha_desc()
            .paginar(filtro.pagina, filtro.limite)
            .construir()
        )
        cursor = self._col.aggregate(pipeline)
        resultados = await cursor.to_list(length=1)

        if not resultados:
            return [], 0

        resultado = resultados[0]
        pendientes = [self._doc_a_entidad(doc) for doc in resultado.get("resultado", [])]
        return pendientes, resultado.get("total_elementos", 0)

    def _entidad_a_doc(self, pendiente: MovimientoPendiente) -> dict:
        doc = pendiente.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(pendiente.creado_por.id_persona)
        if pendiente.confirmado_por:
            doc["confirmado_por"]["id_persona"] = ObjectId(pendiente.confirmado_por.id_persona)
        if pendiente.movimiento_id:
            doc["movimiento_id"] = ObjectId(pendiente.movimiento_id)
        return doc

    def _doc_a_entidad(self, doc: dict) -> MovimientoPendiente:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("confirmado_por"):
            doc["confirmado_por"]["id_persona"] = str(doc["confirmado_por"]["id_persona"])
        if doc.get("movimiento_id"):
            doc["movimiento_id"] = str(doc["movimiento_id"])
        return MovimientoPendiente(**doc)


def _filtro_a_match(filtro: ListarMovimientosPendientesInput) -> dict[str, Any]:
    condiciones: list[dict[str, Any]] = []

    if filtro.estado:
        condiciones.append({"estado": filtro.estado})
    if filtro.tipo_propuesto:
        condiciones.append({"tipo_propuesto": filtro.tipo_propuesto})
    if filtro.creado_por_id:
        condiciones.append({"creado_por.id_persona": ObjectId(filtro.creado_por_id)})

    if not condiciones:
        return {}
    if len(condiciones) == 1:
        return condiciones[0]
    return {"$and": condiciones}
