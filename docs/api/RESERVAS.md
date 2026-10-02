# API — Módulo de Reservas

**Base:** `/api/reservas` · **Auth:** Bearer token (todos los endpoints)

Carrito de trabajo temporal por sesión: aparta stock mientras se arma una salida, sin
comprometerlo hasta que se confirme (confirmación = módulo `movimientos`, todavía no
disponible).

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Sin paginación.

## 2. Tipos y enums

```json
// ReservaResponse
{
  "id": "...", "session_id": "session_abc123", "datos_adicionales": { "cliente": "Juan" },
  "ultima_actividad": "2026-08-08T15:45:44.112Z",
  "items": [{ "producto_codigo": "100", "ubicacion": "A10-1", "cantidad": 10 }]
}

// StockDisponibleResponse
{ "producto_codigo": "100", "ubicacion": "A10-1", "stock_fisico": 100, "reservado_otros": 20, "reservado_actual": 10, "disponible": 70 }
```

`POST .../ajustar` puede devolver un `ReservaResponse` **o** `{ "message": "..." }` si el
ajuste vació el carrito por completo (ver ⚠️ en Flujos).

## 3. Flujos

- **Armar una salida**: por cada producto que el operador agrega al carrito, `POST
  .../ajustar` con `diferencia` positiva. Para quitar, `diferencia` negativa.
- ⚠️ **Si un ajuste negativo deja el carrito sin items, el carrito se elimina solo** — la
  respuesta pasa de `ReservaResponse` a `{"message": "..."}`. El frontend debe manejar
  ambas formas de respuesta en el mismo endpoint.
- **Consultar antes de reservar**: `GET /stock-disponible/...` con `?session_id=` propio
  para saber cuánto más se puede agregar sin que el servidor lo rechace.
- ⚠️ **Solo un `super_admin` puede `DELETE` un carrito ajeno o propio** — un `operativo`
  recibe 403 aunque sea su propio carrito; para vaciarlo debe usar ajustes negativos.

## 4. Endpoints

### GET `/api/reservas/stock-disponible/{producto_codigo}/{ubicacion}` — disponibilidad · `require_authenticated`

Query opcional: `?session_id=...` (si se omite, `reservado_actual` siempre da `0`).
Error: `UBIC-002` (404, no existe esa ubicación para el producto).

### GET `/api/reservas/{session_id}` — obtiene el carrito · `require_authenticated`

Sin restricción de dueño — cualquier autenticado puede consultar cualquier `session_id`.
Error: `RES-002` (404).

### POST `/api/reservas/{session_id}/ajustar` — agrega/quita items · `require_authenticated`

```json
{
  "ajustes": [{ "producto_codigo": "100", "ubicacion": "A10-1", "diferencia": 10 }],
  "datos_adicionales": { "cliente": "Juan", "notas": "..." }
}
```
Varios ajustes por request, cada uno con su propio signo. `datos_adicionales` es opcional y
reemplaza el valor anterior solo si se envía (no se borra si se omite).
Errores: `RES-003` (400, stock disponible insuficiente para algún ajuste positivo), `UBIC-002` (404, ubicación referenciada no existe).

### DELETE `/api/reservas/{session_id}` — elimina el carrito completo · **`require_super_admin`**

Error: `RES-002` (404).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `RES-001` | 400 | La reserva debe tener al menos un item | No debería verse desde el frontend (validación interna) |
| `RES-002` | 404 | No existe una reserva para esa sesión | Tratar como carrito vacío |
| `RES-003` | 400 | Stock disponible insuficiente | Mostrar `disponible` del error y sugerir bajar la cantidad |
| `UBIC-002` | 404 | La ubicación referenciada no existe | Revisar el selector de ubicación en el formulario |

## Notas de comportamiento

- Un carrito abandonado **expira solo a los 3 días de inactividad** (TTL de Mongo) — no hace falta limpiarlo manualmente, y no queda ningún stock "fantasma" bloqueado al expirar.
- No hay endpoint para confirmar la reserva como salida real todavía — eso es responsabilidad de `movimientos` (pendiente de construir), y ahí también será exclusivo de `super_admin`.
- La disponibilidad se recalcula siempre en vivo — no hay caché que pueda desincronizarse.
