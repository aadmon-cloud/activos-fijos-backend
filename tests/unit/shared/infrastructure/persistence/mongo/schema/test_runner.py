from unittest.mock import AsyncMock, MagicMock

from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)
from shared.infrastructure.persistence.mongo.schema.runner import (
    _index_matches,
    sincronizar_coleccion,
)


class _CursorFalso:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self._generar()

    async def _generar(self):
        for item in self._items:
            yield item


class _ColeccionFalsa:
    def __init__(self, indices_existentes):
        self.list_indexes = MagicMock(return_value=_CursorFalso(indices_existentes))
        self.create_indexes = AsyncMock()
        self.drop_index = AsyncMock()


class _DBFalsa:
    def __init__(self, nombres_colecciones, indices_existentes=None):
        self.list_collection_names = AsyncMock(return_value=nombres_colecciones)
        self.create_collection = AsyncMock()
        self.command = AsyncMock()
        self.coleccion = _ColeccionFalsa(indices_existentes or [])

    def __getitem__(self, _nombre):
        return self.coleccion


def _definicion():
    return MongoCollectionDefinition(
        name="cosas",
        validator={"$jsonSchema": {"bsonType": "object", "required": ["codigo"]}},
        indexes=[
            MongoIndexDefinition(name="uq_cosas_codigo", keys=[("codigo", 1)], unique=True),
            MongoIndexDefinition(name="idx_cosas_fecha", keys=[("fecha", -1)]),
        ],
    )


def _doc_indice(nombre, keys, **extra):
    return {"name": nombre, "key": dict(keys), **extra}


# _index_matches


def test_index_matches_identico():
    declarado = MongoIndexDefinition(name="uq_x", keys=[("codigo", 1)], unique=True)
    existente = _doc_indice("uq_x", [("codigo", 1)], unique=True)
    assert _index_matches(declarado, existente) is True


def test_index_matches_claves_distintas():
    declarado = MongoIndexDefinition(name="idx_x", keys=[("codigo", 1)])
    existente = _doc_indice("idx_x", [("otro_campo", 1)])
    assert _index_matches(declarado, existente) is False


def test_index_matches_unique_distinto():
    declarado = MongoIndexDefinition(name="uq_x", keys=[("codigo", 1)], unique=True)
    existente = _doc_indice("uq_x", [("codigo", 1)], unique=False)
    assert _index_matches(declarado, existente) is False


def test_index_matches_ttl_distinto():
    declarado = MongoIndexDefinition(
        name="ttl_x", keys=[("fecha", 1)], expire_after_seconds=3600
    )
    existente = _doc_indice("ttl_x", [("fecha", 1)], expireAfterSeconds=7200)
    assert _index_matches(declarado, existente) is False


# sincronizar_coleccion — colección nueva


async def test_coleccion_nueva_dry_run_no_crea_nada():
    db = _DBFalsa(nombres_colecciones=[])
    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=True, drop_extra_indexes=False
    )

    assert resultado.accion_coleccion == "se_crearia"
    db.create_collection.assert_not_called()
    assert {i.nombre: i.accion for i in resultado.indices} == {
        "uq_cosas_codigo": "se_crearia",
        "idx_cosas_fecha": "se_crearia",
    }
    db.coleccion.create_indexes.assert_not_called()


async def test_coleccion_nueva_se_crea_con_indices():
    db = _DBFalsa(nombres_colecciones=[])
    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=False
    )

    assert resultado.accion_coleccion == "creada"
    db.create_collection.assert_called_once()
    assert db.coleccion.create_indexes.call_count == 2


# sincronizar_coleccion — colección existente


async def test_indice_existente_sin_cambios():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=False
    )

    assert resultado.accion_coleccion == "actualizada_validator"
    db.command.assert_called_once()
    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["uq_cosas_codigo"] == "sin_cambios"
    assert acciones["idx_cosas_fecha"] == "sin_cambios"
    db.coleccion.create_indexes.assert_not_called()


async def test_indice_faltante_se_crea():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=False
    )

    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["idx_cosas_fecha"] == "creado"
    db.coleccion.create_indexes.assert_called_once()


async def test_indice_con_definicion_distinta_reporta_conflicto_y_no_lo_toca():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=False),  # distinto: no unique
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=False
    )

    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["uq_cosas_codigo"] == "conflicto"
    db.coleccion.create_indexes.assert_not_called()
    db.coleccion.drop_index.assert_not_called()


async def test_indice_extra_sin_drop_solo_reporta():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
        _doc_indice("idx_extra_no_declarado", [("legacy_field", 1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=False
    )

    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["idx_extra_no_declarado"] == "extra"
    db.coleccion.drop_index.assert_not_called()


async def test_indice_extra_con_drop_dry_run_no_elimina():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
        _doc_indice("idx_extra_no_declarado", [("legacy_field", 1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=True, drop_extra_indexes=True
    )

    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["idx_extra_no_declarado"] == "se_eliminaria"
    db.coleccion.drop_index.assert_not_called()


async def test_indice_extra_con_drop_real_elimina():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
        _doc_indice("idx_extra_no_declarado", [("legacy_field", 1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=True
    )

    acciones = {i.nombre: i.accion for i in resultado.indices}
    assert acciones["idx_extra_no_declarado"] == "eliminado"
    db.coleccion.drop_index.assert_called_once_with("idx_extra_no_declarado")


async def test_indice_id_nunca_se_elimina():
    existentes = [
        _doc_indice("_id_", [("_id", 1)]),
        _doc_indice("uq_cosas_codigo", [("codigo", 1)], unique=True),
        _doc_indice("idx_cosas_fecha", [("fecha", -1)]),
    ]
    db = _DBFalsa(nombres_colecciones=["cosas"], indices_existentes=existentes)

    resultado = await sincronizar_coleccion(
        db, _definicion(), dry_run=False, drop_extra_indexes=True
    )

    nombres_reportados = {i.nombre for i in resultado.indices}
    assert "_id_" not in nombres_reportados
    db.coleccion.drop_index.assert_not_called()
