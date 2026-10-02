from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.services.proponer_salida import (
    ProponerSalidaService,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
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
    return ProponerSalidaService(movimiento_pendiente_repository_mock)


async def test_crea_una_propuesta_pendiente_de_tipo_salida(service):
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=5, ubicacion="A10-1")

    pendiente = await service.ejecutar(entrada, _audit_persona())

    assert pendiente.id == "pend-1"
    assert pendiente.tipo_propuesto == "salida"
    assert pendiente.estado == "pendiente"
    assert pendiente.payload["ubicacion"] == "A10-1"
