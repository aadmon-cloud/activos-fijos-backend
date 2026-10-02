# Módulo `inventario_reportes`

> Estado: **CERRADO — último módulo del plan de migración**. Ver `MIGRATION_PLAN.md`.
> No introduce entidades ni colección propia: es puro composición de lectura sobre
> `productos` y `movimientos`, consumidos exclusivamente por puerto.

## Responsabilidad

Exponer vistas agregadas de solo lectura sobre el inventario: estadísticas de dashboard,
productos bajo stock mínimo, valor total del inventario y un reporte consolidado. Ningún
endpoint escribe nada — es información derivada, siempre calculada en el momento.

## Entidades

Ninguna propia. Reutiliza `Producto` (de `productos`) y `Movimiento` (de `movimientos`)
tal cual, sin envolverlos en una entidad de dominio nueva.

## Casos de uso (servicios)

| Servicio | Qué hace | Permiso |
|---|---|---|
| `ObtenerEstadisticasDashboardService` | Total de productos, conteo de productos bajo stock, últimos 10 movimientos, conteo de movimientos de hoy | `require_authenticated` |
| `ListarProductosBajoStockService` | Lista completa de productos con `stock_actual < stock_minimo` | `require_authenticated` |
| `ObtenerValorTotalInventarioService` | `sum(stock_actual * precio_unitario)` sobre todos los productos | `require_authenticated` |
| `ObtenerReporteInventarioService` | Compone los 3 anteriores en una sola respuesta (paridad con el legacy) | `require_authenticated` |

## Colección Mongo

Ninguna — no hay persistencia propia.

## Dependencias con otros módulos

Consume `ProductoRepositoryPort` (de `productos`) y `MovimientoRepositoryPort` (de
`movimientos`), ambos **solo por puerto, nunca por repositorio concreto** — este módulo es
el primer caso del plan que compone lectura de dos módulos a la vez, usado como referencia
para validar que el patrón de composición funciona en la práctica.

- `MovimientoRepositoryPort.listar()` se reutiliza sin cambios: `ListarMovimientosInput(pagina=1, limite=10)`
  da los últimos movimientos (ya ordenados `fecha desc` por el pipeline existente);
  `ListarMovimientosInput(fecha_desde=hoy_inicio, limite=1)` da el conteo de "movimientos de
  hoy" leyendo `total_elementos`, descartando la lista.
- `ProductoRepositoryPort.listar_paginado(1, 1)` se reutiliza para el conteo total de
  productos (mismo criterio: se usa `total_elementos`, no la lista).
- `ProductoRepositoryPort` fue **extendido** (propiedad de `productos`, sin riesgo de
  ciclo — mismo criterio que `EjecutorDeMovimientosPort`) con 2 métodos nuevos:
  - `listar_bajo_stock() -> list[Producto]` — `find({"$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}})`.
  - `calcular_valor_total() -> float` — único `$group`/`$sum` real del módulo.
  El conteo de "bajo stock" del dashboard se deriva con `len()` sobre `listar_bajo_stock()`,
  evitando un tercer método solo para contar.

## Flujos principales

1. `GET /dashboard` — estadísticas agregadas.
2. `GET /bajo-stock` — lista completa de productos bajo su mínimo.
3. `GET /valor-total` — valor total del inventario.
4. `GET /reporte` — consolidado de los 3 anteriores.

## Notas de comportamiento

- **El legacy dejaba los 5 endpoints equivalentes completamente públicos** (sin
  `require_authenticated` ni `require_super_admin`) — verificado leyendo
  `routers/inventario.py` completo. Decisión explícita del desarrollador: todos los
  endpoints nuevos exigen `require_authenticated`, igual que el resto de lecturas ya
  migradas en `productos`/`movimientos`.
- **`get_historial_completo_producto` no existe en el `crud.py` legacy** — el endpoint
  `GET /inventario/producto/{id}/historial` lo invocaba igual, produciendo un
  `AttributeError` no controlado si se llamaba (nunca funcionó). Decisión explícita: **no
  se migra**, queda fuera de alcance — `GET /api/movimientos?producto_codigo=X` (ya
  migrado en `movimientos`) resuelve la misma necesidad componiendo desde el frontend.
- **`get_estadisticas_dashboard` legacy devolvía `productos_bajo_stock` como conteo**,
  mientras que `/bajo-stock`/`/reporte` lo devolvían como **lista**, mismo nombre para dos
  formas distintas. Corregido con nombres explícitos: `productos_bajo_stock_conteo: int` en
  el dashboard, `productos_bajo_stock: list[Producto]` en el listado/reporte.
- **La consulta de "bajo stock" es un `find()` con `$expr`, no un pipeline de
  `aggregate`** — el plan original lo generalizaba como agregación; solo "valor total" usa
  un `$group` real.
- **`ReporteInventario`/`InventarioProducto` del legacy (`models.py`/`schemas.py`) no se
  copiaron** — estaban duplicadas entre ambos archivos con `Producto`/`Movimiento`
  subyacentes incompatibles entre sí (una versión con `id: int` estilo SQL legacy), y
  ninguna se usaba como `response_model` real en el router. Los DTOs de salida
  (`EstadisticasDashboardOutput`, `ReporteInventarioOutput`) se diseñaron desde cero.
- **Fuera de alcance**: endpoint propio de "historial de producto" (ver arriba) y
  cualquier endpoint de exportación (`GET /movimientos/exportar/excel` ya vive, migrado y
  con auth, dentro de `movimientos` — no es parte de este módulo).

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `inventario_reportes`": Fase 0 con 3 decisiones
acordadas con el desarrollador (rol requerido, alcance del historial de producto, alcance
del reporte consolidado).

## Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

`super_admin` + 2 productos de prueba (uno bajo su `stock_minimo`, otro con stock suficiente
tras una entrada real) → `GET /dashboard` sin auth (401) → con auth (200, conteos
correctos) → `GET /bajo-stock` incluye solo el producto bajo mínimo → `GET /valor-total`
coincide exactamente con `stock_actual * precio_unitario` del producto con stock → `GET
/reporte` consistente con los 3 anteriores. `productos`/`movimientos` (legacy) verificados
intactos antes y después. Datos de prueba eliminados. Suite completa: **329/329 tests
verdes** (320 previos + 9 nuevos: 3 en el repositorio Mongo de `productos` para
`listar_bajo_stock`/`calcular_valor_total`, y 6 de aplicación en `inventario_reportes` — 3
del dashboard, 1 de bajo-stock, 1 de valor-total, 1 del reporte consolidado).

---

Con el cierre de este módulo, **la migración completa de `inventarios/app/` al backend
hexagonal queda terminada** — no quedan módulos pendientes en `MIGRATION_PLAN.md`.
