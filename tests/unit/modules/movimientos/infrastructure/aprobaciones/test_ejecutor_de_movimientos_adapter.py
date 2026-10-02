from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    ItemSalidaMultipleInput,
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.infrastructure.aprobaciones.ejecutor_de_movimientos_adapter import (
    MovimientosEjecutorAdapter,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


@pytest.fixture
def registrar_entrada_mock():
    return AsyncMock()


@pytest.fixture
def registrar_entrada_multiple_mock():
    return AsyncMock()


@pytest.fixture
def registrar_salida_mock():
    return AsyncMock()


@pytest.fixture
def registrar_salida_multiple_mock():
    return AsyncMock()


@pytest.fixture
def adapter(
    registrar_entrada_mock,
    registrar_entrada_multiple_mock,
    registrar_salida_mock,
    registrar_salida_multiple_mock,
):
    return MovimientosEjecutorAdapter(
        registrar_entrada_mock,
        registrar_entrada_multiple_mock,
        registrar_salida_mock,
        registrar_salida_multiple_mock,
    )


async def test_registrar_entrada_delega_y_pasa_el_uow(adapter, registrar_entrada_mock):
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10)
    creado_por = _audit_persona()
    uow_falso = object()

    await adapter.registrar_entrada(entrada, creado_por, uow_falso)

    registrar_entrada_mock.ejecutar.assert_called_once_with(entrada, creado_por, uow=uow_falso)


async def test_registrar_entrada_multiple_delega_y_pasa_el_uow(
    adapter, registrar_entrada_multiple_mock
):
    entrada = RegistrarEntradaMultipleInput(
        productos=[ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=1)],
        tipo_origen="compra",
        origen_nombre="Proveedor X",
    )
    creado_por = _audit_persona()
    uow_falso = object()

    await adapter.registrar_entrada_multiple(entrada, creado_por, uow_falso)

    registrar_entrada_multiple_mock.ejecutar.assert_called_once_with(
        entrada, creado_por, uow=uow_falso
    )


async def test_registrar_salida_delega_y_pasa_el_uow(adapter, registrar_salida_mock):
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=5, ubicacion="A10-1")
    creado_por = _audit_persona()
    uow_falso = object()

    await adapter.registrar_salida(entrada, creado_por, uow_falso)

    registrar_salida_mock.ejecutar.assert_called_once_with(entrada, creado_por, uow=uow_falso)


async def test_registrar_salida_multiple_delega_y_pasa_el_uow(
    adapter, registrar_salida_multiple_mock
):
    entrada = RegistrarSalidaMultipleInput(
        productos=[
            ItemSalidaMultipleInput(producto_codigo="PROD-001", cantidad=1, ubicacion="A10-1")
        ],
        motivo="Salida de prueba",
    )
    creado_por = _audit_persona()
    uow_falso = object()

    await adapter.registrar_salida_multiple(entrada, creado_por, uow_falso)

    registrar_salida_multiple_mock.ejecutar.assert_called_once_with(
        entrada, creado_por, uow=uow_falso
    )
