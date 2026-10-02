# Módulo `mercados_predefinidos`

> Estado: **incremento 1 completo** (CRUD completo). Ver `MIGRATION_PLAN.md`.

## Responsabilidad

Mantener catálogos de "kits" de productos predefinidos (ej. `KIT_BASICO`) usados para
agilizar salidas masivas sin seleccionar producto por producto. Es un catálogo de
configuración, no transaccional.

## Entidades

- **`MercadoPredefinido`** (`domain/entities/mercado_predefinido.py`): `id`, `nombre`
  (único, inmutable — es la clave de búsqueda), `descripcion`, `productos: list[ProductoKit]`,
  `activo`, `creado_por`, `actualizado_por`.
  - `crear()` / `actualizar()` (`nombre` no editable) — ambos rechazan `productos` vacío.
- **`ProductoKit`** (value object embebido): `producto_id`, `cantidad`, `producto_nombre`
  (resuelto en vivo al crear/actualizar, no se confía en lo que manda el cliente).

## Casos de uso (servicios)

| Servicio | Qué hace |
|---|---|
| `CrearMercadoPredefinidoService` | Valida nombre único + cada `producto_id` contra `productos`, resuelve `producto_nombre` en vivo |
| `ActualizarMercadoPredefinidoService` | Update parcial; si viene `productos`, re-resuelve todos los nombres |
| `ListarMercadosPredefinidosService` | Sin paginar (catálogo chico por naturaleza); filtro `solo_activos` |
| `ObtenerMercadoPredefinidoService` | Por nombre |

## Colecciones Mongo

- **`catalogo_mercados_predefinidos`** (no `mercados_predefinidos` — colisión con 7 kits
  reales del legacy). Índice único en `nombre`.

## Dependencias con otros módulos

Depende de `productos` (`ProductoRepositoryPort`, solo lectura, para validar y resolver
`producto_nombre`).

## Flujos principales

1. **Crear/editar kit**: cada `producto_id` referenciado debe existir en `catalogo_productos`
   — si no, `PROD-002` (404). El `producto_nombre` guardado siempre refleja el nombre real
   del producto al momento de la escritura, nunca lo que mande el cliente.
2. **Listar**: por defecto solo activos (`solo_activos=true`); `?solo_activos=false` trae todos.

## Notas de comportamiento

- `nombre` es la clave de negocio y es **inmutable** — no hay forma de renombrar un kit ya creado.
- Rutas propias bajo `/api/mercados-predefinidos` (el legacy las tenía mezcladas bajo `/movimientos/mercados`).

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `mercados_predefinidos`": el hallazgo de que
crear/actualizar nunca se expusieron por HTTP en el legacy (código muerto a nivel de API),
que los datos reales de producción (7 kits) no coinciden con la semilla que documentaba el
código, y la corrección del bug de `producto_nombre` desactualizado.
