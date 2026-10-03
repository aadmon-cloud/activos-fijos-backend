from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.catalogos.domain.entities import Lugar, TipoLugar
from modules.catalogos.infrastructure.persistence.mongo.lugar_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona


def test_entidad_a_doc_convierte_sede_id_a_object_id():
    sede_id = str(ObjectId())
    lugar = Lugar(
        id=None,
        nombre="Bodega",
        tipo=TipoLugar.BODEGA,
        sede_id=sede_id,
        creado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )

    doc = _entidad_a_doc(lugar)

    assert "id" not in doc
    assert doc["sede_id"] == ObjectId(sede_id)
    assert doc["tipo"] == "bodega"


def test_doc_a_entidad_convierte_object_id_a_string_y_tipo_a_enum():
    object_id = ObjectId()
    sede_id = ObjectId()
    doc = {
        "_id": object_id,
        "nombre": "Bodega",
        "tipo": "bodega",
        "sede_id": sede_id,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    lugar = _doc_a_entidad(doc)

    assert lugar.id == str(object_id)
    assert lugar.sede_id == str(sede_id)
    assert lugar.tipo == TipoLugar.BODEGA


@patch("modules.catalogos.infrastructure.persistence.mongo.lugar_repository.mongo_manager")
async def test_crear_indices_crea_el_indice_compuesto_y_el_indice_de_sede(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"lugares": coleccion_mock}

    await crear_indices()

    coleccion_mock.create_index.assert_any_call(
        [("sede_id", 1), ("nombre", 1)], name="uq_sede_nombre", unique=True
    )
    coleccion_mock.create_index.assert_any_call("sede_id", name="idx_sede_id")
