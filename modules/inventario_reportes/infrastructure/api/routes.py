from typing import Annotated

from fastapi import APIRouter, Depends

from modules.auth.domain.entities.usuario import Usuario
from modules.inventario_reportes.application.dto.estadisticas_dashboard import (
    EstadisticasDashboardOutput,
)
from modules.inventario_reportes.application.dto.reporte_inventario import (
    ReporteInventarioOutput,
)
from modules.inventario_reportes.application.services.listar_productos_bajo_stock import (
    ListarProductosBajoStockService,
)
from modules.inventario_reportes.application.services.obtener_estadisticas_dashboard import (
    ObtenerEstadisticasDashboardService,
)
from modules.inventario_reportes.application.services.obtener_reporte_inventario import (
    ObtenerReporteInventarioService,
)
from modules.inventario_reportes.application.services.obtener_valor_total_inventario import (
    ObtenerValorTotalInventarioService,
)
from modules.inventario_reportes.infrastructure.api.dependencies import (
    get_listar_productos_bajo_stock_service,
    get_obtener_estadisticas_dashboard_service,
    get_obtener_reporte_inventario_service,
    get_obtener_valor_total_inventario_service,
)
from modules.inventario_reportes.infrastructure.api.schemas import (
    EstadisticasDashboardResponse,
    ReporteInventarioResponse,
    ValorTotalInventarioResponse,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.infrastructure.api.schemas import ItemMovimientoResponse, MovimientoResponse
from modules.productos.domain.entities.producto import Producto
from modules.productos.infrastructure.api.schemas import ProductoResponse
from shared.infrastructure.api.dependencies.auth import require_authenticated

router = APIRouter(prefix="/api/inventario", tags=["inventario-reportes"])


def _producto_response(producto: Producto) -> ProductoResponse:
    return ProductoResponse(
        id=producto.id,
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria=producto.categoria,
        stock_minimo=producto.stock_minimo,
        stock_actual=producto.stock_actual,
        precio_unitario=producto.precio_unitario,
        imagen_url=producto.imagen_url,
    )


def _movimiento_response(movimiento: Movimiento) -> MovimientoResponse:
    return MovimientoResponse(
        id=movimiento.id,
        tipo=movimiento.tipo,
        modalidad=movimiento.modalidad,
        producto_codigo=movimiento.producto_codigo,
        producto_nombre=movimiento.producto_nombre,
        cantidad=movimiento.cantidad,
        motivo=movimiento.motivo,
        tipo_origen=movimiento.tipo_origen,
        origen_nombre=movimiento.origen_nombre,
        cliente_destino=movimiento.cliente_destino,
        ubicacion=movimiento.ubicacion,
        ubicacion_origen=movimiento.ubicacion_origen,
        ubicacion_destino=movimiento.ubicacion_destino,
        notas=movimiento.notas,
        remision=movimiento.remision,
        caso=movimiento.caso,
        referencia=movimiento.referencia,
        numero_cajas=movimiento.numero_cajas,
        kit_nombre=movimiento.kit_nombre,
        nombre_mercado=movimiento.nombre_mercado,
        productos=(
            [ItemMovimientoResponse(**item.model_dump()) for item in movimiento.productos]
            if movimiento.productos
            else None
        ),
        pdf_nombre=movimiento.pdf_nombre,
        usuario=movimiento.creado_por.nombre,
        fecha=movimiento.creado_por.fecha,
    )


def _dashboard_response(salida: EstadisticasDashboardOutput) -> EstadisticasDashboardResponse:
    return EstadisticasDashboardResponse(
        total_productos=salida.total_productos,
        productos_bajo_stock_conteo=salida.productos_bajo_stock_conteo,
        ultimos_movimientos=[_movimiento_response(m) for m in salida.ultimos_movimientos],
        movimientos_hoy=salida.movimientos_hoy,
    )


def _reporte_response(salida: ReporteInventarioOutput) -> ReporteInventarioResponse:
    return ReporteInventarioResponse(
        total_productos=salida.total_productos,
        productos_bajo_stock=[_producto_response(p) for p in salida.productos_bajo_stock],
        valor_total_inventario=salida.valor_total_inventario,
        ultimos_movimientos=[_movimiento_response(m) for m in salida.ultimos_movimientos],
    )


@router.get(
    "/dashboard",
    response_model=EstadisticasDashboardResponse,
    summary="Estadísticas agregadas para el dashboard de inventario",
)
async def obtener_estadisticas_dashboard(
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ObtenerEstadisticasDashboardService, Depends(get_obtener_estadisticas_dashboard_service)
    ],
) -> EstadisticasDashboardResponse:
    salida = await service.ejecutar()
    return _dashboard_response(salida)


@router.get(
    "/bajo-stock",
    response_model=list[ProductoResponse],
    summary="Lista los productos con stock_actual por debajo de stock_minimo",
)
async def listar_productos_bajo_stock(
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ListarProductosBajoStockService, Depends(get_listar_productos_bajo_stock_service)
    ],
) -> list[ProductoResponse]:
    productos = await service.ejecutar()
    return [_producto_response(p) for p in productos]


@router.get(
    "/valor-total",
    response_model=ValorTotalInventarioResponse,
    summary="Calcula el valor total del inventario (stock_actual * precio_unitario)",
)
async def obtener_valor_total_inventario(
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ObtenerValorTotalInventarioService, Depends(get_obtener_valor_total_inventario_service)
    ],
) -> ValorTotalInventarioResponse:
    valor_total = await service.ejecutar()
    return ValorTotalInventarioResponse(valor_total_inventario=valor_total)


@router.get(
    "/reporte",
    response_model=ReporteInventarioResponse,
    summary="Reporte consolidado: total de productos, bajo stock, valor total y últimos movimientos",
)
async def obtener_reporte_inventario(
    _usuario_actual: Annotated[Usuario, Depends(require_authenticated)],
    service: Annotated[
        ObtenerReporteInventarioService, Depends(get_obtener_reporte_inventario_service)
    ],
) -> ReporteInventarioResponse:
    salida = await service.ejecutar()
    return _reporte_response(salida)
