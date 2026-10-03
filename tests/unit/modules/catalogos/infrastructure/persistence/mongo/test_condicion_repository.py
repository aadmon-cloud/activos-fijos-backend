from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.catalogos.domain.entities import Condicion
from modules.catalogos.infrastructure.persistence.mongo.condicion_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona


def test_entidad_a_doc_incluye_el_color():
    condicion = Condicion(
        id=None,
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )

    doc = _entidad_a_doc(condicion)

    assert "id" not in doc
    assert doc["color"] == "#4CAF50"


def test_doc_a_entidad_convierte_object_id_a_string():
    object_id = ObjectId()
    doc = {
        "_id": object_id,
        "nombre": "Bueno",
        "color": "#4CAF50",
        "descripcion": None,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    condicion = _doc_a_entidad(doc)

    assert condicion.id == str(object_id)
    assert condicion.color == "#4CAF50"


@patch("modules.catalogos.infrastructure.persistence.mongo.condicion_repository.mongo_manager")
async def test_crear_indices_crea_el_indice_unico_de_nombre(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"condiciones": coleccion_mock}

    await crear_indices()

    coleccion_mock.create_index.assert_called_once_with("nombre", name="uq_nombre", unique=True)
