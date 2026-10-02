# API — Módulo de Inventario (Reportes)

> Estado: **CERRADO — último módulo de la migración**. Ver `MIGRATION_PLAN.md`, sección
> "Módulo `inventario_reportes`". A diferencia del legacy (endpoints públicos, sin ningún
> control de acceso), todos los endpoints de este módulo exigen autenticación.

**Base:** `/api/inventario` · **Auth:** Bearer token (todos los endpoints)

Vistas agregadas de solo lectura sobre el inventario: estadísticas para un dashboard,
productos por debajo de su stock mínimo, valor total del inventario y un reporte
consolidado. Ningún endpoint escribe nada — todo se calcula en el momento de la consulta.

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Ninguno de estos
endpoints pagina — devuelven siempre el conjunto completo o un único objeto agregado.

## 2. Tipos y enums

No introduce enums propios. Los productos y movimientos embebidos en las respuestas usan
exactamente el mismo shape que `docs/api/PRODUCTOS.md` (`ProductoResponse`) y
`docs/api/MOVIMIENTOS.md` (`MovimientoResponse`).

```json
// EstadisticasDashboardResponse
{
  "total_productos": 42,
  "productos_bajo_stock_conteo": 3,
  "ultimos_movimientos": [ /* MovimientoResponse[], hasta 10, mas reciente primero */ ],
  "movimientos_hoy": 5
}
```

```json
// ReporteInventarioResponse
{
  "total_productos": 42,
  "productos_bajo_stock": [ /* ProductoResponse[], lista completa */ ],
  "valor_total_inventario": 15230.75,
  "ultimos_movimientos": [ /* MovimientoResponse[], hasta 10 */ ]
}
```

⚠️ **`productos_bajo_stock_conteo` (dashboard) es un número; `productos_bajo_stock`
(bajo-stock/reporte) es la lista completa** — mismo concepto, dos formas distintas según el
endpoint. No confundir uno con otro.

## 3. Flujos

- **Dashboard** (`GET /dashboard`): resumen rápido para una pantalla de inicio — no trae
  la lista completa de productos bajo stock, solo el conteo.
- **Bajo stock** (`GET /bajo-stock`): la lista completa, para una vista de detalle o
  alerta de reabastecimiento.
- **Valor total** (`GET /valor-total`): un solo número, `sum(stock_actual * precio_unitario)`.
- **Reporte consolidado** (`GET /reporte`): combina los tres anteriores en una sola
  respuesta, para evitar 3 llamadas cuando el frontend los necesita todos juntos.
- **Historial de un producto**: no existe un endpoint propio de este módulo (el legacy
  tenía uno roto que nunca funcionó). Usar `GET /api/movimientos?producto_codigo=X` (ver
  `docs/api/MOVIMIENTOS.md`) junto con `GET /api/productos/{codigo}` (ver
  `docs/api/PRODUCTOS.md`).

## 4. Endpoints

### GET `/api/inventario/dashboard` — estadísticas agregadas para el dashboard · `require_authenticated`

Sin parámetros. Respuesta: `EstadisticasDashboardResponse` (200) — ver ejemplo arriba.

### GET `/api/inventario/bajo-stock` — lista productos bajo su mínimo · `require_authenticated`

Sin parámetros. Respuesta (200): `ProductoResponse[]` — mismo shape que
`docs/api/PRODUCTOS.md`, filtrado a `stock_actual < stock_minimo`. Lista vacía si ningún
producto está bajo mínimo (no es un error).

### GET `/api/inventario/valor-total` — valor total del inventario · `require_authenticated`

Sin parámetros.
```json
// Respuesta (200)
{ "valor_total_inventario": 15230.75 }
```

### GET `/api/inventario/reporte` — reporte consolidado · `require_authenticated`

Sin parámetros. Respuesta: `ReporteInventarioResponse` (200) — ver ejemplo arriba. Equivale
a llamar `/dashboard` + `/bajo-stock` + `/valor-total` en una sola respuesta (con
`productos_bajo_stock` como lista completa, igual que `/bajo-stock`, no como conteo).

## Catálogo de errores

Este módulo no define códigos de error propios (`XXX-nnn`) — es de solo lectura y no tiene
casos de negocio que fallen. El único error posible es `401` (sin token) o `403` (token
inválido/expirado), igual que cualquier otro endpoint con `require_authenticated`.

## Notas de comportamiento

- **El legacy dejaba estos 5 endpoints equivalentes completamente públicos, sin ningún
  control de acceso** — corregido: todos exigen `require_authenticated` aquí.
- **No existe un endpoint de "historial de producto"** en este módulo — el legacy lo tenía
  roto (llamaba una función que no existía en el código fuente, nunca funcionó en
  producción) y la necesidad ya está resuelta por `GET /api/movimientos?producto_codigo=X`.
- **`productos_bajo_stock_conteo` vs. `productos_bajo_stock`**: mismo concepto, dos formas
  (conteo en el dashboard, lista completa en bajo-stock/reporte) — ver sección 2.
- Los 4 endpoints son idempotentes y sin efectos secundarios — seguros de sondear
  (polling) desde el frontend sin preocuparse por generar datos duplicados.
