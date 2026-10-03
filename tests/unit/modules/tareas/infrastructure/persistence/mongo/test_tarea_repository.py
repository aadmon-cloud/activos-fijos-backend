from datetime import UTC, datetime

from bson import ObjectId

from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.persistence.mongo.tarea_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
)


def test_entidad_a_doc_no_incluye_el_id():
    tarea = Tarea(
        id=None,
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    doc = _entidad_a_doc(tarea)

    assert "id" not in doc
    assert "_id" not in doc
    assert doc["titulo"] == "Escribir el plan"


def test_doc_a_entidad_convierte_object_id_a_string():
    object_id = ObjectId()
    doc = {
        "_id": object_id,
        "titulo": "Escribir el plan",
        "completada": False,
        "fecha_creacion": datetime(2026, 7, 23, tzinfo=UTC),
    }

    tarea = _doc_a_entidad(doc)

    assert tarea.id == str(object_id)
    assert tarea.titulo == "Escribir el plan"
