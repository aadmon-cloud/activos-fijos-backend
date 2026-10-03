from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.catalogos.domain.entities import Area
from modules.catalogos.infrastructure.persistence.mongo.area_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona


def test_entidad_a_doc_no_incluye_el_id():
    area = Area(
        id=None,
        nombre="Direccion",
        descripcion=None,
        creado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )

    doc = _entidad_a_doc(area)

    assert "id" not in doc
    assert "_id" not in doc
    assert doc["nombre"] == "Direccion"


def test_doc_a_entidad_convierte_object_id_a_string():
    object_id = ObjectId()
    doc = {
        "_id": object_id,
        "nombre": "Direccion",
        "descripcion": None,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    area = _doc_a_entidad(doc)

    assert area.id == str(object_id)
    assert area.nombre == "Direccion"


@patch("modules.catalogos.infrastructure.persistence.mongo.area_repository.mongo_manager")
async def test_crear_indices_crea_el_indice_unico_de_nombre(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"areas": coleccion_mock}

    await crear_indices()

    coleccion_mock.create_index.assert_called_once_with("nombre", name="uq_nombre", unique=True)
