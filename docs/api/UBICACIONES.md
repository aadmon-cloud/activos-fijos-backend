# API — Módulo de Ubicaciones

**Base:** `/api/productos/{codigo}/ubicaciones` · **Auth:** Bearer token (solo en escritura)

Stock físico de un producto distribuido por ubicación. Anidado bajo `productos` porque una
ubicación siempre pertenece a un producto.

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Sin paginación (la
lista de ubicaciones de un producto es siempre completa).

## 2. Tipos y enums

```json
// UbicacionResponse
{ "id": "...", "producto_codigo": "PROD-001", "ubicacion": "A10-1", "stock_fisico": 50, "stock_reservado": 0, "stock_disponible": 50 }
```

`stock_reservado` siempre viaja en `0` en este incremento (ver Notas de comportamiento).

## 3. Flujos

- **Ver stock de un producto**: `GET /api/productos/{codigo}/ubicaciones` devuelve el producto + todas sus ubicaciones.
- **Registrar mercadería nueva**: `POST .../ubicaciones` con la cantidad física.
- **Mover stock entre bodegas**: `POST .../ubicaciones/transferir`. ⚠️ Si el destino no existe, se crea automáticamente.

## 4. Endpoints

### GET `/api/productos/{codigo}/ubicaciones` — producto con sus ubicaciones · público

Error: `PROD-002` (404, no existe el producto).

### POST `/api/productos/{codigo}/ubicaciones` — crea ubicación · `require_authenticated`

```json
{ "ubicacion": "A10-1", "cantidad": 50 }
```
Errores: `PROD-002` (404), `UBIC-001` (409, ya existe esa ubicación para el producto).

### PUT `/api/productos/{codigo}/ubicaciones/{ubicacion}` — actualiza cantidad · `require_authenticated`

```json
{ "cantidad": 80 }
```
Reemplaza el `stock_fisico` (no es un delta). Error: `UBIC-002` (404).

### DELETE `/api/productos/{codigo}/ubicaciones/{ubicacion}` — elimina · `require_authenticated`

Error: `UBIC-002` (404).

### POST `/api/productos/{codigo}/ubicaciones/transferir` — mueve stock · `require_authenticated`

```json
{ "origen": "A10-1", "destino": "A10-2", "cantidad": 20 }
```
Errores: `UBIC-002` (404, origen no existe), `UBIC-003` (400, stock insuficiente en origen).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `UBIC-001` | 409 | Ya existe esa ubicación para el producto | Sugerir editar la existente en vez de crear |
| `UBIC-002` | 404 | No existe esa ubicación para el producto | Refrescar la lista de ubicaciones |
| `UBIC-003` | 400 | Stock insuficiente en la ubicación de origen | Mostrar el stock disponible real junto al error |

## Notas de comportamiento

- `productos.stock_actual` se recalcula automáticamente después de cada creación/edición/eliminación de ubicación — el frontend debe refrescar el producto tras estas operaciones si lo muestra en la misma pantalla.
- `stock_reservado` no lo mantiene este módulo — la disponibilidad real considerando reservas activas se consulta en `docs/api/RESERVAS.md` (`GET /api/reservas/stock-disponible/...`).
- No hay techo de stock máximo al crear/editar — cualquier cantidad `>= 0` es válida.
- ⚠️ **Crear una ubicación o transferir stock deja además un registro en `movimientos`**
  (tipo `creacion_ubicacion`/`transferencia_ubicacion`, visible vía `GET /api/movimientos` —
  ver `docs/api/MOVIMIENTOS.md`). Es un efecto secundario silencioso: estos dos endpoints no
  cambian su respuesta ni agregan campos, solo queda la bitácora. Actualizar/eliminar una
  ubicación **no** genera bitácora (sin precedente en los datos reales).
