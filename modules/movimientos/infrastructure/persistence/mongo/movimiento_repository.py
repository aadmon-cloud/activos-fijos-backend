from __future__ import annotations

import re
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.infrastructure.persistence.mongo.pipelines.movimiento_pipeline import (
    MovimientoPipelineBuilder,
)
from shared.application.persistence.unit_of_work import UnitOfWorkPort

COLECCION = "registro_movimientos"


class MongoMovimientoRepository(MovimientoRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def crear(self, movimiento: Movimiento, uow: UnitOfWorkPort | None = None) -> Movimiento:
        session = uow.session if uow else None
        nuevo_id = ObjectId()
        movimiento_con_id = movimiento.model_copy(update={"id": str(nuevo_id)})
        doc = self._entidad_a_doc(movimiento_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc, session=session)
        return movimiento_con_id

    async def obtener_por_id(self, movimiento_id: str) -> Movimiento | None:
        if not ObjectId.is_valid(movimiento_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(movimiento_id)})
        return self._doc_a_movimiento(doc) if doc else None

    async def actualizar(
        self, movimiento: Movimiento, uow: UnitOfWorkPort | None = None
    ) -> Movimiento:
        session = uow.session if uow else None
        doc = self._entidad_a_doc(movimiento)
        await self._col.replace_one({"_id": ObjectId(movimiento.id)}, doc, session=session)
        return movimiento

    async def listar(self, filtro: ListarMovimientosInput) -> tuple[list[Movimiento], int]:
        match = _filtro_listar_a_match(filtro)
        pipeline = (
            MovimientoPipelineBuilder()
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
        movimientos = [self._doc_a_movimiento(doc) for doc in resultado.get("resultado", [])]
        return movimientos, resultado.get("total_elementos", 0)

    async def listar_para_exportar(
        self, filtro: ExportarMovimientosExcelInput
    ) -> list[Movimiento]:
        match = _filtro_exportar_a_match(filtro)
        cursor = self._col.find(match).sort("creado_por.fecha", -1)
        docs = await cursor.to_list(length=None)
        return [self._doc_a_movimiento(doc) for doc in docs]

    def _entidad_a_doc(self, movimiento: Movimiento) -> dict:
        doc = movimiento.model_dump(exclude={"id"})
        doc["creado_por"]["id_persona"] = ObjectId(movimiento.creado_por.id_persona)
        if movimiento.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(
                movimiento.actualizado_por.id_persona
            )
        return doc

    def _doc_a_movimiento(self, doc: dict) -> Movimiento:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(doc["actualizado_por"]["id_persona"])
        return Movimiento(**doc)


def _filtro_listar_a_match(filtro: ListarMovimientosInput) -> dict[str, Any]:
    condiciones: list[dict[str, Any]] = []

    if filtro.producto_codigo:
        condiciones.append(
            {
                "$or": [
                    {"producto_codigo": filtro.producto_codigo},
                    {"productos.producto_codigo": filtro.producto_codigo},
                ]
            }
        )
    if filtro.tipo:
        condiciones.append({"tipo": filtro.tipo})
    if filtro.motivo:
        condiciones.append({"motivo": filtro.motivo})
    if filtro.remision:
        condiciones.append({"remision": filtro.remision})
    if filtro.caso:
        condiciones.append({"caso": filtro.caso})
    if filtro.origen_destino:
        patron = re.escape(filtro.origen_destino)
        condiciones.append(
            {
                "$or": [
                    {"origen_nombre": {"$regex": patron, "$options": "i"}},
                    {"cliente_destino": {"$regex": patron, "$options": "i"}},
                ]
            }
        )

    rango_fecha = _rango_fecha(filtro.fecha_desde, filtro.fecha_hasta)
    if rango_fecha:
        condiciones.append({"creado_por.fecha": rango_fecha})

    return _combinar(condiciones)


def _filtro_exportar_a_match(filtro: ExportarMovimientosExcelInput) -> dict[str, Any]:
    condiciones: list[dict[str, Any]] = []
    if filtro.tipo:
        condiciones.append({"tipo": filtro.tipo})
    rango_fecha = _rango_fecha(filtro.fecha_desde, filtro.fecha_hasta)
    if rango_fecha:
        condiciones.append({"creado_por.fecha": rango_fecha})
    return _combinar(condiciones)


def _rango_fecha(fecha_desde, fecha_hasta) -> dict[str, Any]:
    rango: dict[str, Any] = {}
    if fecha_desde:
        rango["$gte"] = fecha_desde
    if fecha_hasta:
        rango["$lte"] = fecha_hasta
    return rango


def _combinar(condiciones: list[dict[str, Any]]) -> dict[str, Any]:
    if not condiciones:
        return {}
    if len(condiciones) == 1:
        return condiciones[0]
    return {"$and": condiciones}
