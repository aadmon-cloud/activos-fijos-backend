from datetime import UTC, datetime

import pytest

from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.domain.errors import ReservaSinItemsError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona(fecha=None):
    return AuditPersona(id_persona="user-id", nombre="operativo", fecha=fecha or datetime.now(UTC))


def _items():
    return [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=5)]


def test_crear_reserva_con_datos_validos():
    creado_por = _audit_persona()
    reserva = Reserva.crear("session-1", _items(), {"cliente": "Juan"}, creado_por)

    assert reserva.session_id == "session-1"
    assert len(reserva.items) == 1
    assert reserva.ultima_actividad == creado_por.fecha
    assert reserva.id is None


def test_crear_reserva_sin_items_lanza_error():
    with pytest.raises(ReservaSinItemsError):
        Reserva.crear("session-1", [], None, _audit_persona())


def test_aplicar_ajuste_suma_a_item_existente():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())
    actualizador = _audit_persona()

    ajustada = reserva.aplicar_ajuste("100", "A10-1", 3, actualizador)

    assert ajustada.items == [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=8)]
    assert ajustada.actualizado_por == actualizador
    assert ajustada.ultima_actividad == actualizador.fecha


def test_aplicar_ajuste_no_muta_la_reserva_original():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())

    reserva.aplicar_ajuste("100", "A10-1", 3, _audit_persona())

    assert reserva.items[0].cantidad == 5


def test_aplicar_ajuste_crea_item_nuevo_si_diferencia_positiva():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())

    ajustada = reserva.aplicar_ajuste("200", "B1-1", 10, _audit_persona())

    assert len(ajustada.items) == 2
    assert ItemReserva(producto_codigo="200", ubicacion="B1-1", cantidad=10) in ajustada.items


def test_aplicar_ajuste_negativo_sobre_item_inexistente_no_hace_nada():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())

    ajustada = reserva.aplicar_ajuste("999", "Z1-1", -5, _audit_persona())

    assert ajustada.items == reserva.items


def test_aplicar_ajuste_elimina_item_si_cantidad_llega_a_cero():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())

    ajustada = reserva.aplicar_ajuste("100", "A10-1", -5, _audit_persona())

    assert ajustada.items == []
    assert ajustada.sin_items is True


def test_aplicar_ajuste_elimina_item_si_cantidad_queda_negativa():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())

    ajustada = reserva.aplicar_ajuste("100", "A10-1", -999, _audit_persona())

    assert ajustada.items == []


def test_sin_items_false_cuando_hay_items():
    reserva = Reserva.crear("session-1", _items(), None, _audit_persona())
    assert reserva.sin_items is False
