from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel

from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)


@dataclass
class ResultadoIndice:
    nombre: str
    coleccion: str
    accion: str  # creado | se_crearia | sin_cambios | conflicto | extra | eliminado | se_eliminaria
    detalle: str = ""


@dataclass
class ResultadoColeccion:
    nombre: str
    existia: bool
    accion_coleccion: str
    indices: list[ResultadoIndice] = field(default_factory=list)


def _index_matches(declarado: MongoIndexDefinition, existente: dict[str, Any]) -> bool:
    """Compara un índice declarado contra el documento que retorna `list_indexes`."""
    claves_declaradas = list(declarado.keys)
    claves_existentes = list(existente.get("key", {}).items())
    if claves_declaradas != claves_existentes:
        return False
    if bool(existente.get("unique", False)) != declarado.unique:
        return False
    if bool(existente.get("sparse", False)) != declarado.sparse:
        return False
    if existente.get("expireAfterSeconds") != declarado.expire_after_seconds:
        return False
    if (declarado.partial_filter_expression or None) != existente.get(
        "partialFilterExpression"
    ):
        return False
    return True


def _a_index_model(indice: MongoIndexDefinition) -> IndexModel:
    return IndexModel(indice.keys, **indice.to_driver_kwargs())


async def sincronizar_coleccion(
    db: AsyncIOMotorDatabase,
    definicion: MongoCollectionDefinition,
    *,
    dry_run: bool,
    drop_extra_indexes: bool,
) -> ResultadoColeccion:
    """Sincroniza una colección: crea o actualiza (`collMod`) y revisa índices.

    En `dry_run=True` nunca se muta MongoDB — solo se reporta la acción planeada.
    """
    nombres_existentes = await db.list_collection_names()
    existia = definicion.name in nombres_existentes

    if not existia:
        if dry_run:
            resultado = ResultadoColeccion(
                nombre=definicion.name,
                existia=False,
                accion_coleccion="se_crearia",
            )
        else:
            await db.create_collection(
                definicion.name, **definicion.to_create_collection_kwargs()
            )
            resultado = ResultadoColeccion(
                nombre=definicion.name, existia=False, accion_coleccion="creada"
            )
    else:
        if dry_run:
            resultado = ResultadoColeccion(
                nombre=definicion.name,
                existia=True,
                accion_coleccion="se_actualizaria_validator",
            )
        else:
            await db.command(
                {
                    "collMod": definicion.name,
                    "validator": definicion.validator,
                    "validationLevel": definicion.validation_level,
                    "validationAction": definicion.validation_action,
                }
            )
            resultado = ResultadoColeccion(
                nombre=definicion.name,
                existia=True,
                accion_coleccion="actualizada_validator",
            )

    indices_existentes: dict[str, dict[str, Any]] = {}
    if existia:
        async for indice_doc in db[definicion.name].list_indexes():
            indices_existentes[indice_doc["name"]] = indice_doc

    nombres_declarados = {indice.name for indice in definicion.indexes}

    for indice in definicion.indexes:
        existente = indices_existentes.get(indice.name)
        if existente is None:
            if dry_run:
                resultado.indices.append(
                    ResultadoIndice(indice.name, definicion.name, "se_crearia")
                )
            else:
                await db[definicion.name].create_indexes([_a_index_model(indice)])
                resultado.indices.append(
                    ResultadoIndice(indice.name, definicion.name, "creado")
                )
        elif _index_matches(indice, existente):
            resultado.indices.append(
                ResultadoIndice(indice.name, definicion.name, "sin_cambios")
            )
        else:
            resultado.indices.append(
                ResultadoIndice(
                    indice.name,
                    definicion.name,
                    "conflicto",
                    detalle="Definicion distinta a la existente; requiere revision manual.",
                )
            )

    if existia:
        for nombre_existente, _doc in indices_existentes.items():
            if nombre_existente == "_id_" or nombre_existente in nombres_declarados:
                continue
            if drop_extra_indexes:
                if dry_run:
                    resultado.indices.append(
                        ResultadoIndice(nombre_existente, definicion.name, "se_eliminaria")
                    )
                else:
                    await db[definicion.name].drop_index(nombre_existente)
                    resultado.indices.append(
                        ResultadoIndice(nombre_existente, definicion.name, "eliminado")
                    )
            else:
                resultado.indices.append(
                    ResultadoIndice(nombre_existente, definicion.name, "extra")
                )

    return resultado


async def sincronizar_colecciones(
    db: AsyncIOMotorDatabase,
    definiciones: list[MongoCollectionDefinition],
    *,
    dry_run: bool = False,
    solo: list[str] | None = None,
    drop_extra_indexes: bool = False,
) -> list[ResultadoColeccion]:
    seleccionadas = (
        [d for d in definiciones if d.name in solo] if solo else definiciones
    )
    resultados = []
    for definicion in seleccionadas:
        resultado = await sincronizar_coleccion(
            db,
            definicion,
            dry_run=dry_run,
            drop_extra_indexes=drop_extra_indexes,
        )
        resultados.append(resultado)
    return resultados
