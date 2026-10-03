from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.solicitudes.domain.entities import (
    EntradaSeguimiento,
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _solicitud(**overrides) -> Solicitud:
    valores = dict(
        id=None,
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id=str(ObjectId()),
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=["http://ejemplo.com/foto.jpg"],
        estado=EstadoSolicitud.PENDIENTE,
        rol_asignado="mantenimiento",
        area_id=None,
        seguimiento=[
            EntradaSeguimiento(
                autor=_AUDIT, comentario="Visto", estado_anterior=None, estado_nuevo=None
            )
        ],
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Solicitud(**valores)


def test_entidad_a_doc_convierte_activo_id_y_mantiene_seguimiento():
    solicitud = _solicitud()

    doc = _entidad_a_doc(solicitud)

    assert "id" not in doc
    assert doc["activo_id"] == ObjectId(solicitud.activo_id)
    assert doc["area_id"] is None
    assert len(doc["seguimiento"]) == 1
    assert doc["seguimiento"][0]["comentario"] == "Visto"


def test_entidad_a_doc_convierte_area_id_cuando_viene_informado():
    area_id = str(ObjectId())
    solicitud = _solicitud(rol_asignado=None, area_id=area_id)

    doc = _entidad_a_doc(solicitud)

    assert doc["area_id"] == ObjectId(area_id)


def test_doc_a_entidad_convierte_object_id_a_string_y_reconstruye_seguimiento():
    object_id = ObjectId()
    activo_id = ObjectId()
    doc = {
        "_id": object_id,
        "tipo": "cambio",
        "activo_id": activo_id,
        "descripcion": "desc",
        "prioridad": "alta",
        "evidencias": [],
        "estado": "en_proceso",
        "rol_asignado": "tecnologia",
        "area_id": None,
        "seguimiento": [
            {
                "autor": {"id_persona": "0", "nombre": "Sistema", "fecha": datetime(2026, 1, 1, tzinfo=UTC)},
                "comentario": "Visto",
                "estado_anterior": "pendiente",
                "estado_nuevo": "en_proceso",
            }
        ],
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    solicitud = _doc_a_entidad(doc)

    assert solicitud.id == str(object_id)
    assert solicitud.activo_id == str(activo_id)
    assert solicitud.tipo == TipoSolicitud.CAMBIO
    assert solicitud.estado == EstadoSolicitud.EN_PROCESO
    assert len(solicitud.seguimiento) == 1
    assert solicitud.seguimiento[0].estado_nuevo == "en_proceso"


@patch("modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository.mongo_manager")
async def test_crear_indices_crea_los_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion_mock}

    await crear_indices()

    nombres = {c.kwargs.get("name") for c in coleccion_mock.create_index.call_args_list}
    assert nombres == {
        "idx_activo_id",
        "idx_estado",
        "idx_rol_asignado",
        "idx_area_id",
        "idx_creado_por_id",
    }
