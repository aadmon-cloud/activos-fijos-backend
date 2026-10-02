from datetime import UTC, datetime

import pytest

from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from modules.movimientos.domain.errors import (
    MovimientoSinProductosError,
    MovimientoUbicacionRequeridaError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def test_registrar_entrada_con_ubicacion_explicita():
    movimiento = Movimiento.registrar_entrada(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=10,
        motivo="Compra",
        tipo_origen="compra",
        origen_nombre="Proveedor X",
        ubicacion="A10-1",
        notas=None,
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "entrada"
    assert movimiento.modalidad == "individual"
    assert movimiento.ubicacion == "A10-1"
    assert movimiento.remision is None
    assert movimiento.id is None


def test_registrar_entrada_sin_ubicacion_usa_almacen_general():
    movimiento = Movimiento.registrar_entrada(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=10,
        motivo=None,
        tipo_origen=None,
        origen_nombre=None,
        ubicacion=None,
        notas=None,
        creado_por=_audit_persona(),
    )

    assert movimiento.ubicacion == "ALMACEN_GENERAL"


def test_registrar_salida_con_datos_validos():
    movimiento = Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo="Salida rápida",
        cliente_destino="Cliente Y",
        ubicacion="A10-1",
        notas=None,
        remision="RM-001",
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "individual"
    assert movimiento.remision == "RM-001"


def test_registrar_salida_sin_ubicacion_lanza_error():
    with pytest.raises(MovimientoUbicacionRequeridaError):
        Movimiento.registrar_salida(
            producto_codigo="PROD-001",
            producto_nombre="Arroz",
            cantidad=5,
            motivo=None,
            cliente_destino=None,
            ubicacion="   ",
            notas=None,
            remision="RM-001",
            creado_por=_audit_persona(),
        )


def test_registrar_kit_con_datos_validos():
    productos = [
        ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=3),
        ItemMovimiento(producto_codigo="PROD-002", producto_nombre="Aceite", cantidad=1),
    ]

    movimiento = Movimiento.registrar_kit(
        kit_nombre="Mercado Básico",
        productos=productos,
        cliente_destino="Cliente Y",
        notas="nota",
        caso="CASO-1",
        remision="RM-001",
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "kit"
    assert movimiento.cantidad == 1
    assert movimiento.motivo == "Salida de Kit"
    assert movimiento.numero_cajas == 0
    assert movimiento.kit_nombre == "Mercado Básico"
    assert movimiento.productos == productos
    assert movimiento.producto_codigo is None


def test_registrar_entrada_multiple_con_datos_validos():
    productos = [
        ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=3, ubicacion="A10-1"),
        ItemMovimiento(producto_codigo="PROD-002", producto_nombre="Aceite", cantidad=2, ubicacion="A10-2"),
    ]

    movimiento = Movimiento.registrar_entrada_multiple(
        productos=productos,
        tipo_origen="compra",
        origen_nombre="Proveedor X",
        notas="nota",
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "entrada"
    assert movimiento.modalidad == "entrada_multiple"
    assert movimiento.cantidad == 5
    assert movimiento.motivo == "Compra"
    assert movimiento.productos == productos
    assert movimiento.producto_codigo is None


def test_registrar_entrada_multiple_sin_productos_lanza_error():
    with pytest.raises(MovimientoSinProductosError):
        Movimiento.registrar_entrada_multiple(
            productos=[],
            tipo_origen="compra",
            origen_nombre="Proveedor X",
            notas=None,
            creado_por=_audit_persona(),
        )


def test_registrar_multiple_con_motivo_fijo_para_confirmar_reserva():
    productos = [
        ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=5, ubicacion="A10-1"),
    ]

    movimiento = Movimiento.registrar_multiple(
        productos=productos,
        motivo="Entrega de Ayudas/Unidades",
        cliente_destino="Cliente Y",
        notas=None,
        caso="CASO-1",
        remision="RM-001",
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "multiple"
    assert movimiento.cantidad == 1
    assert movimiento.motivo == "Entrega de Ayudas/Unidades"
    assert movimiento.numero_cajas == 0
    assert movimiento.productos == productos
    assert movimiento.kit_nombre is None


def test_registrar_multiple_sin_productos_lanza_error():
    with pytest.raises(MovimientoSinProductosError):
        Movimiento.registrar_multiple(
            productos=[],
            motivo="Salida múltiple",
            cliente_destino=None,
            notas=None,
            caso=None,
            remision="RM-001",
            creado_por=_audit_persona(),
        )


def test_registrar_mercado_con_datos_validos():
    productos = [
        ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=6, ubicacion="A10-1"),
    ]

    movimiento = Movimiento.registrar_mercado(
        nombre_mercado="Mercado Básico",
        productos=productos,
        cantidad=2,
        cliente_destino="Cliente Y",
        notas=None,
        referencia="REF-1",
        remision="RM-001",
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "mercado"
    assert movimiento.cantidad == 2
    assert movimiento.motivo == "Salida de Mercado Básico"
    assert movimiento.nombre_mercado == "Mercado Básico"
    assert movimiento.referencia == "REF-1"
    assert movimiento.productos == productos


def test_registrar_mercado_sin_productos_lanza_error():
    with pytest.raises(MovimientoSinProductosError):
        Movimiento.registrar_mercado(
            nombre_mercado="Mercado Básico",
            productos=[],
            cantidad=1,
            cliente_destino=None,
            notas=None,
            referencia=None,
            remision="RM-001",
            creado_por=_audit_persona(),
        )


def test_registrar_creacion_ubicacion():
    movimiento = Movimiento.registrar_creacion_ubicacion(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        ubicacion="A10-1",
        cantidad=50,
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "creacion_ubicacion"
    assert movimiento.modalidad == "individual"
    assert movimiento.ubicacion == "A10-1"
    assert movimiento.cantidad == 50
    assert movimiento.ubicacion_origen is None
    assert movimiento.ubicacion_destino is None


def test_registrar_transferencia_ubicacion():
    movimiento = Movimiento.registrar_transferencia_ubicacion(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        ubicacion_origen="A10-1",
        ubicacion_destino="A10-2",
        cantidad=20,
        creado_por=_audit_persona(),
    )

    assert movimiento.tipo == "transferencia_ubicacion"
    assert movimiento.modalidad == "individual"
    assert movimiento.ubicacion_origen == "A10-1"
    assert movimiento.ubicacion_destino == "A10-2"
    assert movimiento.cantidad == 20
    assert movimiento.ubicacion is None


def test_adjuntar_pdf_firmado_no_muta_el_original():
    movimiento = Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        cliente_destino=None,
        ubicacion="A10-1",
        notas=None,
        remision="RM-001",
        creado_por=_audit_persona(),
    )
    actualizador = _audit_persona()

    actualizado = movimiento.adjuntar_pdf_firmado("pdfs/salidas/x.pdf", "firmado.pdf", actualizador)

    assert actualizado.pdf_firmado == "pdfs/salidas/x.pdf"
    assert actualizado.pdf_nombre == "firmado.pdf"
    assert actualizado.actualizado_por == actualizador
    assert movimiento.pdf_firmado is None
