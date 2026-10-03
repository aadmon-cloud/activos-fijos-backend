from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from bson.decimal128 import Decimal128

from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
    crear_indices,
)
from shared.domain.entities.audit import AuditPersona


def _activo(**overrides) -> Activo:
    valores = dict(
        id=None,
        nombre="Laptop",
        numero_inventario="INV-001",
        tipo=TipoActivo.ACTIVO_FIJO,
        marca=None,
        modelo=None,
        serie=None,
        descripcion=None,
        categoria_id=str(ObjectId()),
        area_id=str(ObjectId()),
        responsable_id=str(ObjectId()),
        condicion_id=str(ObjectId()),
        estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
        sede_id=str(ObjectId()),
        lugar_id=str(ObjectId()),
        valor=Decimal("1500000.50"),
        fecha_adquisicion=datetime(2026, 1, 1, tzinfo=UTC),
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Activo(**valores)


def test_entidad_a_doc_convierte_referencias_a_object_id_y_valor_a_decimal128():
    activo = _activo()

    doc = _entidad_a_doc(activo)

    assert "id" not in doc
    assert doc["categoria_id"] == ObjectId(activo.categoria_id)
    assert doc["area_id"] == ObjectId(activo.area_id)
    assert isinstance(doc["valor"], Decimal128)
    assert doc["valor"].to_decimal() == Decimal("1500000.50")
    assert doc["estado_ciclo_vida"] == "disponible"


def test_doc_a_entidad_convierte_object_id_a_string_y_decimal128_a_decimal():
    object_id = ObjectId()
    categoria_id = ObjectId()
    doc = {
        "_id": object_id,
        "nombre": "Laptop",
        "numero_inventario": "INV-001",
        "tipo": "activo_fijo",
        "marca": None,
        "modelo": None,
        "serie": None,
        "descripcion": None,
        "categoria_id": categoria_id,
        "area_id": ObjectId(),
        "responsable_id": ObjectId(),
        "condicion_id": ObjectId(),
        "estado_ciclo_vida": "prestado",
        "sede_id": ObjectId(),
        "lugar_id": ObjectId(),
        "valor": Decimal128("1500000.50"),
        "fecha_adquisicion": datetime(2026, 1, 1, tzinfo=UTC),
        "complementos": [{"nombre": "Cargador", "descripcion": None, "cantidad": 1, "serie": None}],
        "observaciones": None,
        "foto_url": None,
        "ficha_tecnica_url": None,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    activo = _doc_a_entidad(doc)

    assert activo.id == str(object_id)
    assert activo.categoria_id == str(categoria_id)
    assert activo.valor == Decimal("1500000.50")
    assert activo.estado_ciclo_vida == EstadoCicloVida.PRESTADO
    assert len(activo.complementos) == 1
    assert activo.complementos[0].nombre == "Cargador"


@patch("modules.activos.infrastructure.persistence.mongo.activo_repository.mongo_manager")
async def test_crear_indices_crea_los_indices_esperados(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}

    await crear_indices()

    nombres = {c.kwargs.get("name") for c in coleccion_mock.create_index.call_args_list}
    assert nombres == {
        "uq_numero_inventario",
        "idx_area_id",
        "idx_categoria_id",
        "idx_responsable_id",
        "idx_condicion_id",
        "idx_estado_ciclo_vida",
        "idx_sede_id",
        "idx_lugar_id",
    }
