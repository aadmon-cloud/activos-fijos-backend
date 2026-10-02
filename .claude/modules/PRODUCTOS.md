# Módulo `productos`

> Estado: **incremento 1 completo** (CRUD básico). Pendientes para incrementos futuros: carga
> masiva Excel, código de barras/QR, subir/eliminar imagen. Ver `MIGRATION_PLAN.md`.

## Responsabilidad

Catálogo maestro de productos: alta, edición, baja, búsqueda. Es el módulo base del que
dependen `ubicaciones`, `mercados_predefinidos` y `reservas`.

## Entidades

- **`Producto`** (`domain/entities/producto.py`): `id`, `codigo` (identificador público,
  único, inmutable), `nombre`, `descripcion`, `categoria`, `stock_minimo`, `stock_actual`
  (denormalizado — ver Notas), `precio_unitario`, `imagen_url` (incremento futuro),
  `creado_por`, `actualizado_por`.
  - `crear()` — código ya resuelto por el service (provisto o autogenerado).
  - `actualizar()` — update parcial; **no** permite tocar `codigo`, `stock_actual` ni `imagen_url`.
  - `recalcular_stock(nuevo_stock_actual)` — distinto de `actualizar()`; lo usa
    exclusivamente `ubicaciones` para mantener la proyección de stock total.

## Casos de uso (servicios)

| Servicio | Qué hace |
|---|---|
| `CrearProductoService` | Autogenera código (`PROD-YYYYMMDD-XXXXXX`) si no se provee; valida unicidad |
| `ActualizarProductoService` | Update parcial por código |
| `EliminarProductoService` | Baja por código |
| `ObtenerProductoService` | Lectura por código |
| `ListarProductosService` | Paginado |
| `BuscarProductosService` | Texto libre sobre nombre/código/descripción (`$regex` escapado) |

## Colecciones Mongo

- **`catalogo_productos`** (no `productos` — colisión con datos reales del legacy). Índices:
  único en `codigo`, texto en `nombre`, normal en `categoria`, `stock_actual`,
  `creado_por.fecha`.

## Dependencias con otros módulos

Ninguna hacia adentro (solo `shared` para autenticación). Expone `ProductoRepositoryPort` y
`Producto.recalcular_stock()`, consumidos por `ubicaciones` (recalcula `stock_actual`),
`mercados_predefinidos` (resuelve `producto_nombre` en vivo) y `reservas` (vía
`ubicaciones`, para leer `stock_fisico`).

`ProductoRepositoryPort` fue extendido (sin tocar los métodos existentes) con
`listar_bajo_stock()` y `calcular_valor_total()` para que `inventario_reportes` los consuma
en modo solo-lectura — mismo criterio que las extensiones previas de puertos: el módulo
proveedor (`productos`) es dueño del puerto porque no hay riesgo de ciclo.

## Flujos principales

1. **Alta**: `POST /api/productos` (requiere auth) — código opcional, precio opcional
   (default 0.0, se acepta desde la creación).
2. **Búsqueda**: `GET /api/productos/buscar?q=...` — sin autenticación, regex case-insensitive
   sobre nombre/código/descripción.
3. **Edición/baja**: `PUT`/`DELETE /api/productos/{codigo}` — requieren auth.

## Notas de comportamiento

- **`stock_actual` es una proyección, no se edita directamente** desde este módulo — la
  fuente de verdad es la suma de `ubicaciones` (ver módulo `ubicaciones`). `ActualizarProductoService`
  explícitamente no acepta ese campo.
- El identificador público en todas las rutas es `codigo`, nunca el `_id` de Mongo.

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `productos`": corrección del bug legacy de
`precio_unitario` no persistido al crear, corrección de seguridad (`re.escape()`) en la
búsqueda por texto, y por qué el índice de texto no es el que resuelve la búsqueda real
(usa `$regex`, no `$text`).
