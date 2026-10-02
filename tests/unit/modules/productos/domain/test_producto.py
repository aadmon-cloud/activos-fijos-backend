from datetime import UTC, datetime

from modules.productos.domain.entities.producto import Producto
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def test_crear_producto_con_datos_validos():
    producto = Producto.crear(
        codigo="PROD-001",
        nombre="  Laptop HP  ",
        descripcion="  Elite Book  ",
        categoria="Electrónica",
        stock_minimo=5,
        precio_unitario=999.99,
        creado_por=_audit_persona(),
    )

    assert producto.codigo == "PROD-001"
    assert producto.nombre == "Laptop HP"
    assert producto.descripcion == "Elite Book"
    assert producto.categoria == "Electrónica"
    assert producto.stock_minimo == 5
    assert producto.precio_unitario == 999.99
    assert producto.stock_actual == 0
    assert producto.imagen_url is None
    assert producto.id is None


def test_crear_producto_sin_descripcion_ni_categoria():
    producto = Producto.crear(
        codigo="PROD-002",
        nombre="Mouse",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )

    assert producto.descripcion is None
    assert producto.categoria is None


def test_actualizar_aplica_solo_los_campos_provistos():
    producto = Producto.crear(
        codigo="PROD-003",
        nombre="Teclado",
        descripcion="Mecánico",
        categoria="Periféricos",
        stock_minimo=2,
        precio_unitario=50.0,
        creado_por=_audit_persona(),
    )

    actualizador = AuditPersona(id_persona="otro-id", nombre="otro", fecha=datetime.now(UTC))
    actualizado = producto.actualizar(actualizador, nombre="Teclado mecánico")

    assert actualizado.nombre == "Teclado mecánico"
    assert actualizado.descripcion == "Mecánico"
    assert actualizado.categoria == "Periféricos"
    assert actualizado.stock_minimo == 2
    assert actualizado.precio_unitario == 50.0
    assert actualizado.actualizado_por == actualizador


def test_actualizar_no_muta_el_producto_original():
    producto = Producto.crear(
        codigo="PROD-004",
        nombre="Monitor",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )

    actualizado = producto.actualizar(_audit_persona(), nombre="Monitor 4K")

    assert producto.nombre == "Monitor"
    assert actualizado.nombre == "Monitor 4K"


def test_actualizar_no_permite_tocar_codigo_ni_stock_actual_ni_imagen():
    producto = Producto.crear(
        codigo="PROD-005",
        nombre="Silla",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )

    actualizado = producto.actualizar(_audit_persona(), nombre="Silla ergonómica")

    assert actualizado.codigo == "PROD-005"
    assert actualizado.stock_actual == 0
    assert actualizado.imagen_url is None


def test_recalcular_stock_actualiza_solo_stock_actual():
    producto = Producto.crear(
        codigo="PROD-006",
        nombre="Escritorio",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )

    recalculado = producto.recalcular_stock(42)

    assert recalculado.stock_actual == 42
    assert recalculado.codigo == producto.codigo
    assert recalculado.nombre == producto.nombre


def test_recalcular_stock_no_muta_el_producto_original():
    producto = Producto.crear(
        codigo="PROD-007",
        nombre="Archivador",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )

    producto.recalcular_stock(10)

    assert producto.stock_actual == 0
