from datetime import UTC, datetime

from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from modules.movimientos.infrastructure.pdf.reportlab_comprobante import (
    ReportlabComprobanteAdapter,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


async def test_genera_comprobante_individual():
    movimiento = Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        cliente_destino="Cliente Y",
        ubicacion="A10-1",
        notas="una nota",
        remision="RM-001",
        creado_por=_audit_persona(),
    )
    adaptador = ReportlabComprobanteAdapter()

    contenido = await adaptador.generar_comprobante_salida(movimiento)

    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 100


async def test_genera_comprobante_kit():
    movimiento = Movimiento.registrar_kit(
        kit_nombre="Mercado Básico",
        productos=[
            ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=3),
            ItemMovimiento(producto_codigo="PROD-002", producto_nombre="Aceite", cantidad=1),
        ],
        cliente_destino="Cliente Y",
        notas=None,
        caso="CASO-1",
        remision="RM-002",
        creado_por=_audit_persona(),
    )
    adaptador = ReportlabComprobanteAdapter()

    contenido = await adaptador.generar_comprobante_salida(movimiento)

    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 100


async def test_genera_comprobante_multiple():
    movimiento = Movimiento.registrar_multiple(
        productos=[
            ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=3),
        ],
        motivo="Entrega de Ayudas/Unidades",
        cliente_destino="Cliente Y",
        notas=None,
        caso=None,
        remision="RM-003",
        creado_por=_audit_persona(),
    )
    adaptador = ReportlabComprobanteAdapter()

    contenido = await adaptador.generar_comprobante_salida(movimiento)

    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 100


async def test_genera_comprobante_mercado():
    movimiento = Movimiento.registrar_mercado(
        nombre_mercado="Mercado Básico",
        productos=[
            ItemMovimiento(producto_codigo="PROD-001", producto_nombre="Arroz", cantidad=6),
        ],
        cantidad=2,
        cliente_destino="Cliente Y",
        notas=None,
        referencia="REF-1",
        remision="RM-004",
        creado_por=_audit_persona(),
    )
    adaptador = ReportlabComprobanteAdapter()

    contenido = await adaptador.generar_comprobante_salida(movimiento)

    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 100
