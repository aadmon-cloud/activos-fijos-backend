from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.services.proponer_salida_multiple import (
    ProponerSalidaMultipleService,
)
from modules.movimientos.application.dto.registrar_salida_multiple import (
    ItemSalidaMultipleInput,
    RegistrarSalidaMultipleInput,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="usuario-1", nombre="Ana", fecha=datetime.now(UTC))


@pytest.fixture
def movimiento_pendiente_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda pendiente, uow=None: pendiente.model_copy(
        update={"id": "pend-1"}
    )
    return mock


@pytest.fixture
def service(movimiento_pendiente_repository_mock):
    return ProponerSalidaMultipleService(movimiento_pendiente_repository_mock)


async def test_crea_una_propuesta_pendiente_de_tipo_salida_multiple(service):
    entrada = RegistrarSalidaMultipleInput(
        productos=[
            ItemSalidaMultipleInput(producto_codigo="PROD-001", cantidad=3, ubicacion="A10-1")
        ],
        motivo="Entrega especial",
    )

    pendiente = await service.ejecutar(entrada, _audit_persona())

    assert pendiente.id == "pend-1"
    assert pendiente.tipo_propuesto == "salida_multiple"
    assert pendiente.estado == "pendiente"
    assert pendiente.payload["motivo"] == "Entrega especial"
