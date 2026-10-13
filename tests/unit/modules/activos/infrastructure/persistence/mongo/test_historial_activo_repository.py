from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.activos.domain.entities import EntradaHistorialActivo
from modules.activos.infrastructure.persistence.mongo.historial_activo_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona


def test_entidad_a_doc_convierte_activo_id_a_object_id():
    activo_id = str(ObjectId())
    entrada = EntradaHistorialActivo(
        id=None,
        activo_id=activo_id,
        campo="responsable_id",
        valor_anterior="u1",
        valor_nuevo="u2",
        modificado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
    )

    doc = _entidad_a_doc(entrada)

    assert "id" not in doc
    assert doc["activo_id"] == ObjectId(activo_id)
    assert doc["campo"] == "responsable_id"


def test_doc_a_entidad_convierte_object_id_a_string():
    object_id = ObjectId()
    activo_id = ObjectId()
    doc = {
        "_id": object_id,
        "activo_id": activo_id,
        "campo": "estado_ciclo_vida",
        "valor_anterior": "disponible",
        "valor_nuevo": "prestado",
        "modificado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
    }

    entrada = _doc_a_entidad(doc)

    assert entrada.id == str(object_id)
    assert entrada.activo_id == str(activo_id)
    assert entrada.campo == "estado_ciclo_vida"


def test_entidad_a_doc_convierte_una_nota_de_auditoria():
    activo_id = str(ObjectId())
    auditoria_id = str(ObjectId())
    entrada = EntradaHistorialActivo(
        id=None,
        activo_id=activo_id,
        tipo="nota",
        nota="Verificado durante auditoria. Resultado: Encontrado.",
        auditoria_id=auditoria_id,
        modificado_por=AuditPersona(
            id_persona="admin-1", nombre="Admin", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
    )

    doc = _entidad_a_doc(entrada)

    assert doc["tipo"] == "nota"
    assert doc["campo"] is None
    assert doc["nota"] == "Verificado durante auditoria. Resultado: Encontrado."
    assert doc["auditoria_id"] == ObjectId(auditoria_id)


def test_doc_a_entidad_asume_cambio_campo_si_el_documento_no_tiene_tipo():
    doc = {
        "_id": ObjectId(),
        "activo_id": ObjectId(),
        "campo": "area_id",
        "valor_anterior": "a1",
        "valor_nuevo": "a2",
        "modificado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
    }

    entrada = _doc_a_entidad(doc)

    assert entrada.tipo == "cambio_campo"
    assert entrada.nota is None
    assert entrada.auditoria_id is None


def test_doc_a_entidad_convierte_una_nota_de_auditoria():
    auditoria_id = ObjectId()
    doc = {
        "_id": ObjectId(),
        "activo_id": ObjectId(),
        "tipo": "nota",
        "nota": "Reportado como no encontrado durante auditoria.",
        "auditoria_id": auditoria_id,
        "modificado_por": {
            "id_persona": "admin-1",
            "nombre": "Admin",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
    }

    entrada = _doc_a_entidad(doc)

    assert entrada.tipo == "nota"
    assert entrada.campo is None
    assert entrada.nota == "Reportado como no encontrado durante auditoria."
    assert entrada.auditoria_id == str(auditoria_id)


@patch(
    "modules.activos.infrastructure.persistence.mongo.historial_activo_repository.mongo_manager"
)
async def test_crear_indices_crea_el_indice_compuesto(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"activos_historial": coleccion_mock}

    await crear_indices()

    coleccion_mock.create_index.assert_called_once_with(
        [("activo_id", 1), ("modificado_por.fecha", -1)], name="idx_activo_id_fecha"
    )
