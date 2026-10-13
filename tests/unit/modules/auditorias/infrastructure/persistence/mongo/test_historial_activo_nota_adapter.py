from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.auditorias.infrastructure.persistence.mongo.historial_activo_nota_adapter import (
    MongoHistorialActivoNotaAdapter,
)
from shared.domain.entities.audit import AuditPersona

_RUTA = (
    "modules.auditorias.infrastructure.persistence.mongo.historial_activo_nota_adapter."
    "mongo_manager"
)


@patch(_RUTA)
async def test_registrar_nota_inserta_el_documento_con_la_forma_esperada(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"activos_historial": coleccion_mock}
    activo_id = str(ObjectId())
    auditoria_id = str(ObjectId())
    auditor = AuditPersona(id_persona="admin-1", nombre="Admin", fecha=datetime(2026, 1, 1, tzinfo=UTC))

    await MongoHistorialActivoNotaAdapter().registrar_nota(
        activo_id, "Encontrado con novedad.", auditoria_id, auditor
    )

    documento = coleccion_mock.insert_one.call_args.args[0]
    assert documento["activo_id"] == ObjectId(activo_id)
    assert documento["tipo"] == "nota"
    assert documento["nota"] == "Encontrado con novedad."
    assert documento["auditoria_id"] == ObjectId(auditoria_id)
    assert documento["modificado_por"]["id_persona"] == "admin-1"
    assert "campo" not in documento
    assert "valor_anterior" not in documento
