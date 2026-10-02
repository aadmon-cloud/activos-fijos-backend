# API — Módulo de Aprobaciones Pendientes

> Estado: **CERRADO — 1/1 incremento**. Ver `MIGRATION_PLAN.md`, sección "Módulo
> `aprobaciones_pendientes`", para el detalle de la Fase 0 (el legacy nunca implementó
> realmente "confirmar" — este módulo corrige ese comportamiento, no lo reproduce).

**Base:** `/api/aprobaciones-pendientes` · **Auth:** Bearer token (todos los endpoints)

Permite que cualquier usuario autenticado proponga una entrada o salida de inventario sin
poder aplicarla directamente. La propuesta queda en estado `pendiente` hasta que un
**`super_admin`** la confirma (generando el movimiento real en `movimientos`) o alguien
autorizado la elimina. Ningún otro rol, ni siquiera `admin`, puede confirmar.

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Paginación estándar en
el listado (`resultado`, `pagina_actual`, `elementos_por_pagina`, `total_elementos`,
`total_paginas`).

## 2. Tipos y enums

```json
// MovimientoPendienteResponse
{
  "id": "...",
  "tipo_propuesto": "entrada",   // "entrada" | "entrada_multiple" | "salida" | "salida_multiple"
  "payload": {                   // mismos campos que el request que la origino
    "producto_codigo": "PROD-001",
    "cantidad": 10,
    "ubicacion": "A10-1",
    "motivo": null,
    "tipo_origen": null,
    "origen_nombre": null,
    "notas": null
  },
  "estado": "pendiente",         // "pendiente" | "confirmada"
  "movimiento_id": null,         // se completa recien al confirmar
  "propuesto_por": "operativo1",
  "fecha_propuesta": "2026-08-19T16:40:27.825Z",
  "confirmado_por": null,        // nombre de quien confirmo, si ya fue confirmada
  "fecha_confirmacion": null
}
```

⚠️ `payload` refleja el `Input` interno del tipo de movimiento propuesto — su forma exacta
depende de `tipo_propuesto` (ver el body de cada endpoint `POST` más abajo, son los mismos
campos que `movimientos` usa para el registro directo equivalente).

## 3. Flujos

- **Proponer** (`POST /entradas`, `/entradas/multiple`, `/salidas`, `/salidas/multiple`):
  cualquier usuario autenticado — no requiere `super_admin`. No toca stock ni crea ningún
  movimiento real todavía, solo guarda la propuesta.
- **Listar** (`GET ""`): un `super_admin` ve las propuestas de **todos** los usuarios;
  cualquier otro rol solo ve las propias. El filtro de dueño lo decide el backend según el
  rol — no se puede consultar las de otro usuario manipulando query params.
- **Eliminar una** (`DELETE /{id}`): el dueño de la propuesta, o un `super_admin`.
  ⚠️ **Una propuesta ya confirmada no se puede eliminar** — se preserva su historial.
- **Eliminar varias** (`DELETE /eliminar-multiples`): exclusivo `super_admin`, best-effort
  (las que no existen o ya están confirmadas se ignoran silenciosamente, no rompen el lote).
- **Confirmar** (`POST /{id}/confirmar`): exclusivo `super_admin`. Aplica el movimiento real
  (descuenta/suma stock, genera remisión si aplica) y responde con el `Movimiento` real creado
  — mismo shape que `GET /api/movimientos/{id}` (ver `docs/api/MOVIMIENTOS.md`).
  ⚠️ **Punto sin retorno**: una vez confirmada, no se puede volver a confirmar ni eliminar. El
  autor del movimiento real es quien confirma, no quien propuso.

## 4. Endpoints

### POST `/api/aprobaciones-pendientes/entradas` — propone una entrada individual · `require_authenticated`

```json
{
  "producto_codigo": "PROD-001",
  "cantidad": 10,
  "motivo": "Compra",
  "tipo_origen": "compra",
  "origen_nombre": "Proveedor X",
  "ubicacion": "A10-1",
  "notas": null
}
```
Respuesta: `MovimientoPendienteResponse` (201), `estado="pendiente"`.

### POST `/api/aprobaciones-pendientes/entradas/multiple` — propone una entrada con varios productos · `require_authenticated`

```json
{
  "productos": [
    { "producto_codigo": "PROD-001", "cantidad": 10, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "cantidad": 5 }
  ],
  "tipo_origen": "compra",
  "origen_nombre": "Proveedor X",
  "ubicacion": "BODEGA-GLOBAL",
  "notas": null
}
```
Respuesta: `MovimientoPendienteResponse` (201). Error: `422` (`productos` vacío, o
`tipo_origen` fuera del vocabulario válido — mismo catálogo que la entrada múltiple real de
`movimientos`).

### POST `/api/aprobaciones-pendientes/salidas` — propone una salida individual · `require_authenticated`

```json
{
  "producto_codigo": "PROD-001",
  "cantidad": 5,
  "ubicacion": "A10-1",
  "cliente_destino": "Cliente Y",
  "motivo": null,
  "notas": null
}
```
Respuesta: `MovimientoPendienteResponse` (201).

### POST `/api/aprobaciones-pendientes/salidas/multiple` — propone una salida con varios productos · `require_authenticated`

```json
{
  "productos": [
    { "producto_codigo": "PROD-001", "cantidad": 15, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "cantidad": 10, "ubicacion": "A10-2" }
  ],
  "motivo": "Salida combinada",
  "cliente_destino": "Cliente Z",
  "notas": null
}
```
Respuesta: `MovimientoPendienteResponse` (201).

### GET `/api/aprobaciones-pendientes` — lista propuestas paginadas · `require_authenticated`

Query params (opcionales): `estado` (`pendiente`|`confirmada`), `tipo_propuesto` (los 4
valores), `pagina` (default 1), `limite` (default 20, máx 200). `super_admin` ve todas; el
resto solo las propias — sin excepción, no hay parámetro para pedir las de otro usuario.

### DELETE `/api/aprobaciones-pendientes/{id}` — elimina una propuesta · `require_authenticated`

Respuesta: `204` sin body. Errores: `APR-001` (404, no existe), `APR-003` (403, no es el dueño
ni `super_admin`), `APR-002` (409, ya fue confirmada).

### DELETE `/api/aprobaciones-pendientes/eliminar-multiples` — elimina varias de una vez · **`require_super_admin`**

```json
{ "movimientos_pendientes_ids": ["...", "..."] }
```
```json
// Respuesta (200)
{ "eliminadas": 3, "total_solicitadas": 5 }
```
Best-effort: los ids inexistentes o ya confirmados se ignoran (no cuentan como error, solo no
suman a `eliminadas`).

### POST `/api/aprobaciones-pendientes/{id}/confirmar` — confirma la propuesta, aplica el movimiento real · **`require_super_admin`**

Sin body. Respuesta: `MovimientoResponse` (201) — el `Movimiento` real ya creado, mismo shape
que en `movimientos` (ver `docs/api/MOVIMIENTOS.md`, sección 2). Errores: `APR-001` (404, no
existe), `APR-002` (409, ya fue confirmada), y cualquier error propio del movimiento real
subyacente según el tipo (`PROD-002`, `MOV-002`, `MOV-003`, etc. — ver
`docs/api/MOVIMIENTOS.md`).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `APR-001` | 404 | No existe una propuesta con ese id | Refrescar el listado |
| `APR-002` | 409 | La propuesta ya fue confirmada — no se puede confirmar ni eliminar de nuevo | Refrescar el listado, mostrar el movimiento real ya generado |
| `APR-003` | 403 | La propuesta no pertenece a este usuario | Ocultar la acción de eliminar si no es el dueño ni `super_admin` |

Ver también `docs/api/MOVIMIENTOS.md` para los errores propios del movimiento real que puede
devolver `POST /{id}/confirmar` según el tipo propuesto.

## Notas de comportamiento

- **El legacy nunca aplicaba el movimiento real al "confirmar"** — solo cambiaba un campo
  `estado`, sin tocar stock. Este módulo corrige ese comportamiento: confirmar sí genera el
  `Movimiento` real, con las mismas reglas de negocio (stock, remisión, etc.) que el registro
  directo equivalente en `movimientos`.
- **Solo `super_admin` confirma** — decisión explícita, sin excepción para `admin`. Cualquier
  otro rol solo puede proponer.
- **El autor (`creado_por`) del movimiento real generado es quien confirma**, no quien
  propuso — `confirmado_por` en la respuesta de la propuesta registra la misma persona.
- **Confirmar y actualizar la propuesta ocurren en una sola transacción** — no hay ventana en
  la que el movimiento real exista pero la propuesta siga mostrando `estado="pendiente"`.
- **Fuera de alcance**: proponer una salida por mercado predefinido, y proponer la
  confirmación de una reserva — ninguno tuvo precedente en el flujo legacy de pendientes.
