from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.auditorias.domain.entities import (
    Auditoria,
    EstadoAuditoria,
    ItemAuditoria,
    ResultadoVerificacion,
)
from modules.auditorias.infrastructure.persistence.mongo.auditoria_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _item(**overrides) -> ItemAuditoria:
    valores = dict(
        activo_id=str(ObjectId()),
        nombre="Laptop",
        numero_inventario="INV-1",
        tipo="activo_fijo",
        descripcion=None,
        serie=None,
        estado_ciclo_vida_al_inicio="disponible",
        resultado=None,
        observacion=None,
        verificado_en=None,
    )
    valores.update(overrides)
    return ItemAuditoria(**valores)


def _auditoria(**overrides) -> Auditoria:
    valores = dict(
        id=None,
        usuario_auditado_id=str(ObjectId()),
        estado=EstadoAuditoria.EN_PROGRESO,
        items=[_item()],
        fecha_cierre=None,
        pdf_archivo_id=None,
        detalle_error_notificacion=None,
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Auditoria(**valores)


def test_entidad_a_doc_convierte_referencias_y_items():
    auditoria = _auditoria()

    doc = _entidad_a_doc(auditoria)

    assert "id" not in doc
    assert doc["usuario_auditado_id"] == ObjectId(auditoria.usuario_auditado_id)
    assert doc["estado"] == "en_progreso"
    assert doc["items"][0]["activo_id"] == ObjectId(auditoria.items[0].activo_id)
    assert doc["items"][0]["resultado"] is None


def test_entidad_a_doc_convierte_el_resultado_de_un_item_verificado():
    auditoria = _auditoria(
        items=[_item(resultado=ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD, observacion="Danio")]
    )

    doc = _entidad_a_doc(auditoria)

    assert doc["items"][0]["resultado"] == "encontrado_con_novedad"
    assert doc["items"][0]["observacion"] == "Danio"


def test_doc_a_entidad_convierte_object_id_a_string_y_reconstruye_items():
    object_id = ObjectId()
    usuario_id = ObjectId()
    activo_id = ObjectId()
    doc = {
        "_id": object_id,
        "usuario_auditado_id": usuario_id,
        "estado": "finalizada",
        "items": [
            {
                "activo_id": activo_id,
                "nombre": "Laptop",
                "numero_inventario": "INV-1",
                "tipo": "activo_fijo",
                "descripcion": None,
                "serie": None,
                "estado_ciclo_vida_al_inicio": "disponible",
                "resultado": "no_encontrado",
                "observacion": None,
                "verificado_en": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ],
        "fecha_cierre": datetime(2026, 1, 1, tzinfo=UTC),
        "pdf_archivo_id": "archivo-1",
        "detalle_error_notificacion": None,
        "creado_por": {"id_persona": "admin-1", "nombre": "Admin", "fecha": datetime(2026, 1, 1, tzinfo=UTC)},
        "actualizado_por": None,
    }

    auditoria = _doc_a_entidad(doc)

    assert auditoria.id == str(object_id)
    assert auditoria.usuario_auditado_id == str(usuario_id)
    assert auditoria.estado == EstadoAuditoria.FINALIZADA
    assert len(auditoria.items) == 1
    assert auditoria.items[0].activo_id == str(activo_id)
    assert auditoria.items[0].resultado == ResultadoVerificacion.NO_ENCONTRADO
    assert auditoria.pdf_archivo_id == "archivo-1"


@patch("modules.auditorias.infrastructure.persistence.mongo.auditoria_repository.mongo_manager")
async def test_crear_indices_crea_los_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"auditorias": coleccion_mock}

    await crear_indices()

    nombres = {c.kwargs.get("name") for c in coleccion_mock.create_index.call_args_list}
    assert nombres == {"idx_usuario_auditado_id", "idx_estado", "idx_creado_por_id"}
