from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from bson.decimal128 import Decimal128

from modules.mantenimientos.domain.entities import (
    ArchivoMantenimiento,
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from modules.mantenimientos.infrastructure.persistence.mongo.mantenimiento_repository import (
    MongoMantenimientoRepository,
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _mantenimiento(**overrides) -> Mantenimiento:
    valores = dict(
        id=None,
        activo_id=str(ObjectId()),
        solicitud_id=None,
        tipo=TipoMantenimiento.CORRECTIVO,
        tecnico_responsable_id=str(ObjectId()),
        fecha=datetime(2026, 1, 1, tzinfo=UTC),
        observaciones=None,
        costo=Decimal("150000"),
        documentos=[ArchivoMantenimiento(archivo_id="f1", nombre="factura.pdf")],
        evidencias=[],
        estado=EstadoMantenimiento.PROGRAMADO,
        frecuencia_dias=90,
        proxima_fecha_sugerida=datetime(2026, 4, 1, tzinfo=UTC),
        alerta_enviada=False,
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Mantenimiento(**valores)


def test_entidad_a_doc_convierte_referencias_costo_y_documentos():
    mantenimiento = _mantenimiento()

    doc = _entidad_a_doc(mantenimiento)

    assert "id" not in doc
    assert doc["activo_id"] == ObjectId(mantenimiento.activo_id)
    assert doc["solicitud_id"] is None
    assert isinstance(doc["costo"], Decimal128)
    assert doc["costo"].to_decimal() == Decimal("150000")
    assert doc["documentos"] == [{"archivo_id": "f1", "nombre": "factura.pdf"}]


def test_entidad_a_doc_convierte_solicitud_id_cuando_viene_informado():
    solicitud_id = str(ObjectId())
    mantenimiento = _mantenimiento(solicitud_id=solicitud_id)

    doc = _entidad_a_doc(mantenimiento)

    assert doc["solicitud_id"] == ObjectId(solicitud_id)


def test_doc_a_entidad_convierte_object_id_a_string_y_decimal128_a_decimal():
    object_id = ObjectId()
    activo_id = ObjectId()
    tecnico_id = ObjectId()
    doc = {
        "_id": object_id,
        "activo_id": activo_id,
        "solicitud_id": None,
        "tipo": "preventivo",
        "tecnico_responsable_id": tecnico_id,
        "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        "observaciones": None,
        "costo": Decimal128("150000"),
        "documentos": [],
        "evidencias": [{"archivo_id": "f1", "nombre": "foto.png"}],
        "estado": "completado",
        "frecuencia_dias": 90,
        "proxima_fecha_sugerida": datetime(2026, 4, 1, tzinfo=UTC),
        "alerta_enviada": True,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    mantenimiento = _doc_a_entidad(doc)

    assert mantenimiento.id == str(object_id)
    assert mantenimiento.activo_id == str(activo_id)
    assert mantenimiento.tecnico_responsable_id == str(tecnico_id)
    assert mantenimiento.tipo == TipoMantenimiento.PREVENTIVO
    assert mantenimiento.estado == EstadoMantenimiento.COMPLETADO
    assert mantenimiento.costo == Decimal("150000")
    assert mantenimiento.alerta_enviada is True
    assert len(mantenimiento.evidencias) == 1


@patch("modules.mantenimientos.infrastructure.persistence.mongo.mantenimiento_repository.mongo_manager")
async def test_crear_indices_crea_los_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"mantenimientos": coleccion_mock}

    await crear_indices()

    nombres = {c.kwargs.get("name") for c in coleccion_mock.create_index.call_args_list}
    assert nombres == {
        "idx_activo_id",
        "idx_estado",
        "idx_tecnico_responsable_id",
        "idx_solicitud_id",
        "idx_proxima_fecha_sugerida",
    }


_MODULO = "modules.mantenimientos.infrastructure.persistence.mongo.mantenimiento_repository"


@patch(f"{_MODULO}.mongo_manager")
async def test_guardar_varios_inserta_en_bloque_y_conserva_el_orden(mongo_manager_mock):
    id_a, id_b = ObjectId(), ObjectId()
    primero, segundo = _mantenimiento(), _mantenimiento()
    coleccion = MagicMock()
    coleccion.insert_many = AsyncMock(return_value=MagicMock(inserted_ids=[id_a, id_b]))
    cursor = MagicMock()
    # Mongo puede devolver los documentos en otro orden: el resultado debe seguir el de insercion.
    cursor.to_list = AsyncMock(
        return_value=[
            {**_entidad_a_doc(segundo), "_id": id_b},
            {**_entidad_a_doc(primero), "_id": id_a},
        ]
    )
    coleccion.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"mantenimientos": coleccion}

    guardados = await MongoMantenimientoRepository().guardar_varios([primero, segundo])

    assert [g.id for g in guardados] == [str(id_a), str(id_b)]
    documentos = coleccion.insert_many.call_args.args[0]
    assert len(documentos) == 2
    assert documentos[0]["activo_id"] == ObjectId(primero.activo_id)


@patch(f"{_MODULO}.mongo_manager")
async def test_guardar_varios_sin_mantenimientos_no_toca_la_base(mongo_manager_mock):
    assert await MongoMantenimientoRepository().guardar_varios([]) == []

    mongo_manager_mock.get_database.assert_not_called()
