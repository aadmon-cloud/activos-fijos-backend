from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.services.confirmar_movimiento_pendiente import (
    ConfirmarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.domain.errors import MovimientoPendienteNoEncontradoError
from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.dto.registrar_entrada_multiple import (
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.dto.registrar_salida_multiple import (
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.domain.entities.audit_persona import AuditPersona
from tests.unit.modules.aprobaciones_pendientes.application.services._fakes import (
    fake_unit_of_work_factory,
)


def _audit_persona(id_persona="usuario-1"):
    return AuditPersona(id_persona=id_persona, nombre="Ana", fecha=datetime.now(UTC))


def _pendiente(tipo_propuesto, payload):
    return MovimientoPendiente.proponer(
        tipo_propuesto=tipo_propuesto, payload=payload, creado_por=_audit_persona()
    ).model_copy(update={"id": "pend-1"})


def _movimiento_creado():
    return Movimiento.registrar_entrada(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=10,
        motivo=None,
        tipo_origen=None,
        origen_nombre=None,
        ubicacion="A10-1",
        notas=None,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "mov-1"})


@pytest.fixture
def movimiento_pendiente_repository_mock():
    mock = AsyncMock()
    mock.actualizar.side_effect = lambda pendiente, uow=None: pendiente
    return mock


@pytest.fixture
def ejecutor_de_movimientos_mock():
    mock = AsyncMock()
    mock.registrar_entrada.return_value = _movimiento_creado()
    mock.registrar_entrada_multiple.return_value = _movimiento_creado()
    mock.registrar_salida.return_value = _movimiento_creado()
    mock.registrar_salida_multiple.return_value = _movimiento_creado()
    return mock


@pytest.fixture
def service(movimiento_pendiente_repository_mock, ejecutor_de_movimientos_mock):
    return ConfirmarMovimientoPendienteService(
        movimiento_pendiente_repository_mock,
        ejecutor_de_movimientos_mock,
        fake_unit_of_work_factory,
    )


async def test_no_encontrada_lanza_error(service, movimiento_pendiente_repository_mock):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = None

    with pytest.raises(MovimientoPendienteNoEncontradoError):
        await service.ejecutar("pend-1", _audit_persona("admin-1"))


async def test_despacha_a_registrar_entrada(
    service, movimiento_pendiente_repository_mock, ejecutor_de_movimientos_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        "entrada", {"producto_codigo": "PROD-001", "cantidad": 10}
    )
    confirmado_por = _audit_persona("admin-1")

    movimiento = await service.ejecutar("pend-1", confirmado_por)

    ejecutor_de_movimientos_mock.registrar_entrada.assert_called_once()
    entrada_usada = ejecutor_de_movimientos_mock.registrar_entrada.call_args.args[0]
    assert isinstance(entrada_usada, RegistrarEntradaInput)
    assert entrada_usada.producto_codigo == "PROD-001"
    assert movimiento.id == "mov-1"


async def test_despacha_a_registrar_entrada_multiple(
    service, movimiento_pendiente_repository_mock, ejecutor_de_movimientos_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        "entrada_multiple",
        {
            "productos": [{"producto_codigo": "PROD-001", "cantidad": 3, "ubicacion": None}],
            "tipo_origen": "compra",
            "origen_nombre": "Proveedor X",
            "ubicacion": None,
            "notas": None,
        },
    )

    await service.ejecutar("pend-1", _audit_persona("admin-1"))

    ejecutor_de_movimientos_mock.registrar_entrada_multiple.assert_called_once()
    entrada_usada = ejecutor_de_movimientos_mock.registrar_entrada_multiple.call_args.args[0]
    assert isinstance(entrada_usada, RegistrarEntradaMultipleInput)


async def test_despacha_a_registrar_salida(
    service, movimiento_pendiente_repository_mock, ejecutor_de_movimientos_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        "salida", {"producto_codigo": "PROD-001", "cantidad": 5, "ubicacion": "A10-1"}
    )

    await service.ejecutar("pend-1", _audit_persona("admin-1"))

    ejecutor_de_movimientos_mock.registrar_salida.assert_called_once()
    entrada_usada = ejecutor_de_movimientos_mock.registrar_salida.call_args.args[0]
    assert isinstance(entrada_usada, RegistrarSalidaInput)


async def test_despacha_a_registrar_salida_multiple(
    service, movimiento_pendiente_repository_mock, ejecutor_de_movimientos_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        "salida_multiple",
        {
            "productos": [
                {"producto_codigo": "PROD-001", "cantidad": 3, "ubicacion": "A10-1"}
            ],
            "motivo": "Entrega especial",
            "cliente_destino": None,
            "notas": None,
        },
    )

    await service.ejecutar("pend-1", _audit_persona("admin-1"))

    ejecutor_de_movimientos_mock.registrar_salida_multiple.assert_called_once()
    entrada_usada = ejecutor_de_movimientos_mock.registrar_salida_multiple.call_args.args[0]
    assert isinstance(entrada_usada, RegistrarSalidaMultipleInput)


async def test_marca_la_pendiente_como_confirmada_con_referencia_al_movimiento(
    service, movimiento_pendiente_repository_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        "entrada", {"producto_codigo": "PROD-001", "cantidad": 10}
    )
    confirmado_por = _audit_persona("admin-1")

    await service.ejecutar("pend-1", confirmado_por)

    pendiente_actualizada = movimiento_pendiente_repository_mock.actualizar.call_args.args[0]
    assert pendiente_actualizada.estado == "confirmada"
    assert pendiente_actualizada.movimiento_id == "mov-1"
    assert pendiente_actualizada.confirmado_por == confirmado_por
