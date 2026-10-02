# API — Módulo de Movimientos

> Estado: **CERRADO — 6/6 incrementos completos** (movimiento individual + confirmar reserva
> normal/kit/múltiple + comprobante PDF + entrada múltiple + bitácora de `ubicaciones` +
> salida múltiple/por mercado directas). Ver `MIGRATION_PLAN.md`, sección "Módulo
> `movimientos`", para el detalle de los 6 incrementos. Única deuda documentada sin construir:
> "confirmar varias reservas en un comprobante" (sin demanda real hoy). Los endpoints de
> registro directo (`/entradas`, `/entradas/multiple`, `/salidas`, `/salidas/multiple`) tienen
> ahora una vía alternativa para roles no-`super_admin`: proponerlos como pendientes de
> aprobación vía `docs/api/APROBACIONES_PENDIENTES.md`, que un `super_admin` confirma después.
> Para estadísticas agregadas/dashboard sobre estos movimientos, ver
> `docs/api/INVENTARIO_REPORTES.md` (último módulo de la migración).

**Base:** `/api/movimientos` · **Auth:** Bearer token (todos los endpoints)

Registra entradas y salidas individuales de inventario, siendo la única vía legítima (junto
con `ubicaciones`) de alterar `productos.stock_actual`. Cada salida genera automáticamente un
número de remisión secuencial (`RM-001`, `RM-002`, ...).

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Paginación estándar en
el listado (`resultado`, `pagina_actual`, `elementos_por_pagina`, `total_elementos`,
`total_paginas`).

## 2. Tipos y enums

```json
// MovimientoResponse — modalidad "individual" (entrada o salida)
{
  "id": "...",
  "tipo": "entrada",            // "entrada" | "salida" | "creacion_ubicacion" | "transferencia_ubicacion"
  "modalidad": "individual",    // "individual" | "kit" | "entrada_multiple" | "multiple" | "mercado"
  "producto_codigo": "PROD-001",
  "producto_nombre": "Arroz",
  "cantidad": 10,
  "motivo": "Compra",
  "tipo_origen": "compra",      // solo entradas, texto libre
  "origen_nombre": "Proveedor X",
  "cliente_destino": null,      // solo salidas
  "ubicacion": "A10-1",
  "ubicacion_origen": null,     // solo tipo "transferencia_ubicacion" — ver ejemplo abajo
  "ubicacion_destino": null,    // idem
  "notas": null,
  "remision": null,             // "RM-001" en salidas, siempre null en entradas
  "caso": null,
  "referencia": null,           // solo modalidad "mercado"
  "numero_cajas": null,
  "kit_nombre": null,           // solo modalidad "kit"
  "nombre_mercado": null,       // solo modalidad "mercado"
  "productos": null,            // "kit" | "entrada_multiple" | "multiple" | "mercado" — ver ejemplos abajo
  "pdf_nombre": null,           // nombre del PDF firmado subido, si hay uno
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — modalidad "kit" (confirmación de reserva kit)
{
  "id": "...",
  "tipo": "salida",
  "modalidad": "kit",
  "producto_codigo": null,
  "producto_nombre": null,
  "cantidad": 1,                 // siempre 1 — representa "un kit confirmado"
  "motivo": "Salida de Kit",
  "cliente_destino": "Cliente Y",
  "remision": "RM-001",
  "caso": "CASO-99",
  "numero_cajas": 0,             // siempre 0 en este incremento (ver Notas de comportamiento)
  "kit_nombre": "Mercado Básico",
  "productos": [
    { "producto_codigo": "PROD-001", "producto_nombre": "Arroz", "cantidad": 3, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "producto_nombre": "Aceite", "cantidad": 1, "ubicacion": "A10-2" }
  ],
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — modalidad "entrada_multiple"
{
  "id": "...",
  "tipo": "entrada",
  "modalidad": "entrada_multiple",
  "producto_codigo": null,
  "producto_nombre": null,
  "cantidad": 15,                // suma de todos los items
  "motivo": "Compra",            // tipo_origen.capitalize()
  "tipo_origen": "compra",
  "origen_nombre": "Proveedor X",
  "productos": [
    { "producto_codigo": "PROD-001", "producto_nombre": "Arroz", "cantidad": 10, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "producto_nombre": "Aceite", "cantidad": 5, "ubicacion": "BODEGA-GLOBAL" }
  ],
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — modalidad "multiple" (confirmación de reserva múltiple, o salida múltiple directa)
{
  "id": "...",
  "tipo": "salida",
  "modalidad": "multiple",
  "producto_codigo": null,
  "producto_nombre": null,
  "cantidad": 1,                 // siempre 1 — la cantidad real está en cada item embebido
  "motivo": "Entrega de Ayudas/Unidades",  // fijo al confirmar reserva; texto libre en salida directa
  "cliente_destino": "Cliente Y",
  "remision": "RM-001",
  "numero_cajas": 0,
  "productos": [
    { "producto_codigo": "PROD-001", "producto_nombre": "Arroz", "cantidad": 15, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "producto_nombre": "Aceite", "cantidad": 10, "ubicacion": "A10-2" }
  ],
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — modalidad "mercado" (salida por mercado predefinido)
{
  "id": "...",
  "tipo": "salida",
  "modalidad": "mercado",
  "producto_codigo": null,
  "producto_nombre": null,
  "cantidad": 3,                  // multiplicador de mercados solicitado, NO la suma de items
  "motivo": "Salida de Mercado Básico",
  "cliente_destino": "Cliente Y",
  "remision": "RM-002",
  "referencia": "REF-123",
  "nombre_mercado": "Mercado Básico",
  "productos": [
    { "producto_codigo": "PROD-001", "producto_nombre": "Arroz", "cantidad": 6, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "producto_nombre": "Aceite", "cantidad": 3, "ubicacion": "A10-1" }
  ],
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — tipo "creacion_ubicacion" (bitácora, generada por `ubicaciones`)
{
  "id": "...",
  "tipo": "creacion_ubicacion",
  "modalidad": "individual",
  "producto_codigo": "PROD-001",
  "producto_nombre": "Arroz",
  "cantidad": 50,
  "ubicacion": "A10-1",
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}

// MovimientoResponse — tipo "transferencia_ubicacion" (bitácora, generada por `ubicaciones`)
{
  "id": "...",
  "tipo": "transferencia_ubicacion",
  "modalidad": "individual",
  "producto_codigo": "PROD-001",
  "producto_nombre": "Arroz",
  "cantidad": 20,
  "ubicacion": null,
  "ubicacion_origen": "A10-1",
  "ubicacion_destino": "A10-2",
  "usuario": "admin",
  "fecha": "2026-08-19T13:41:22.311Z"
}
```

## 3. Flujos

- **Registrar una entrada**: `POST /entradas`. Si la ubicación no existe todavía para ese
  producto, se crea con el stock recibido; si ya existe, se suma. `productos.stock_actual` se
  recalcula siempre como la suma de **todas** las ubicaciones del producto (no un incremento
  suelto) — es la misma fuente de verdad que usa el módulo `ubicaciones`.
- **Registrar una salida**: `POST /salidas` — **exclusivo de `super_admin`**, a diferencia de
  la entrada. La ubicación es obligatoria y debe tener stock físico suficiente; se valida ahí,
  no contra el total del producto. Genera automáticamente la remisión.
- ⚠️ **La entrada y la salida tienen permisos distintos** — un `operativo`/`admin` puede
  registrar entradas pero recibe 403 al intentar una salida directa.
- **Confirmar una reserva (`reservas`)**: `POST /reservas/{session_id}/confirmar` —
  **exclusivo de `super_admin`**. El backend detecta automáticamente la modalidad de la
  reserva (el frontend no la elige, solo llama al mismo endpoint):
  - Normal → una o más salidas reales (una por producto/ubicación reservado), todas con la
    **misma remisión**.
  - Kit → **una sola** salida con todos los productos embebidos en `productos`.
  - Múltiple → **una sola** salida con todos los productos embebidos, motivo fijo
    `"Entrega de Ayudas/Unidades"`.
  - En los tres casos, la reserva se borra al confirmar.
- ⚠️ **Si la reserva es de una modalidad desconocida, la confirmación se rechaza** (`MOV-004`,
  400) — el frontend debe distinguir esta respuesta de un error de stock/producto. Con las 3
  modalidades reales del legacy ya soportadas, esto solo debería verse ante datos corruptos.
- **Comprobante y PDF firmado**: `GET /{id}/comprobante` genera el PDF de cualquier salida ya
  registrada (individual, kit, múltiple o mercado) — no se genera automáticamente al
  confirmar/registrar, hay que pedirlo explícitamente. `POST /{id}/pdf-firmado` sube el PDF
  firmado a mano (multipart, campo `archivo`); `GET /{id}/pdf-firmado` lo descarga. No existe
  una URL estática para el PDF — siempre se pide a través de estos endpoints.
- **Registrar una entrada múltiple**: `POST /entradas/multiple` — **exclusivo de
  `super_admin`**, igual que la entrada individual — un rol distinto solo puede
  **proponerla** vía `docs/api/APROBACIONES_PENDIENTES.md`. Varios productos en una
  sola entrada, cada uno con su propia ubicación (o la global del request, o
  `ALMACEN_GENERAL`). `tipo_origen` está restringido a un vocabulario fijo
  (`compra`/`donacion`/`devolucion`/`traslado`/`ajuste`), a diferencia de la entrada
  individual donde es texto libre.
- **Registrar una salida múltiple directa**: `POST /salidas/multiple` — **exclusivo de
  `super_admin`**, igual permiso que la salida individual. Varios productos en una sola
  salida, pero a diferencia de la entrada múltiple **cada item debe traer su propia ubicación**
  — no hay ubicación global de fallback.
- **Registrar una salida por mercado predefinido**: `POST /salida-por-mercado` — **exclusivo
  de `super_admin`**. Resuelve los productos del `MercadoPredefinido` por nombre y multiplica
  cada cantidad del kit por el multiplicador solicitado (`cantidad` del request). **Cada
  producto del kit trae su propia ubicación** en `productos` (mismo patrón que
  `/salidas/multiple`) — no existe una única ubicación global para todo el mercado, porque
  cada producto puede vivir en una ubicación física distinta. Si falta la ubicación de algún
  producto del kit en el request, `MOV-009` (400). A diferencia del legacy, este endpoint no
  intenta elegir automáticamente una ubicación con stock suficiente (esa función nunca existió
  realmente en el legacy).
- **Consultar historial**: `GET /` con filtros combinables (por producto, tipo, fecha, motivo,
  remisión, caso, texto libre sobre proveedor/cliente).
- **Exportar a Excel**: `GET /exportar/excel` con filtros de fecha/tipo — descarga un `.xlsx`,
  no un JSON.
- ⚠️ **`creacion_ubicacion`/`transferencia_ubicacion` no se crean desde este módulo** — son
  bitácora generada automáticamente por los endpoints de `ubicaciones`
  (`POST .../ubicaciones` y `POST .../ubicaciones/transferir`, ver `docs/api/UBICACIONES.md`).
  Acá solo se **consultan** vía `GET /` o `GET /exportar/excel` filtrando por ese `tipo`.
- ⚠️ **Fuera de alcance, sin construir**: confirmar varias reservas en un solo comprobante — el
  legacy nunca lo implementó, no hay comportamiento real que preservar.

## 4. Endpoints

### POST `/api/movimientos/entradas` — registra una entrada · **`require_super_admin`**

```json
{
  "producto_codigo": "PROD-001",
  "cantidad": 10,
  "motivo": "Compra",
  "tipo_origen": "compra",
  "origen_nombre": "Proveedor X",
  "ubicacion": "A10-1",         // opcional — default "ALMACEN_GENERAL"
  "notas": null
}
```
Respuesta: `MovimientoResponse` (201). Error: `PROD-002` (404, no existe el producto).

### POST `/api/movimientos/salidas` — registra una salida · **`require_super_admin`**

```json
{
  "producto_codigo": "PROD-001",
  "cantidad": 5,
  "ubicacion": "A10-1",         // obligatorio
  "cliente_destino": "Cliente Y",
  "motivo": null,
  "notas": null
}
```
Respuesta: `MovimientoResponse` (201), con `remision` siempre poblado.
Errores: `PROD-002` (404, no existe el producto), `MOV-002` (404, el producto no tiene esa
ubicación), `MOV-003` (422, stock físico insuficiente en esa ubicación — el detalle incluye
`disponible`/`solicitado`).

### POST `/api/movimientos/entradas/multiple` — registra una entrada con varios productos · **`require_super_admin`**

```json
{
  "productos": [
    { "producto_codigo": "PROD-001", "cantidad": 10, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "cantidad": 5 }             // sin ubicacion propia
  ],
  "tipo_origen": "compra",        // compra | donacion | devolucion | traslado | ajuste
  "origen_nombre": "Proveedor X",
  "ubicacion": "BODEGA-GLOBAL",   // default para items sin ubicacion propia
  "notas": null
}
```
Respuesta: `MovimientoResponse` (201), modalidad `entrada_multiple`, un item embebido por
producto. Errores: `PROD-002` (404, algún producto no existe), `422` (validación: `productos`
vacío, o `tipo_origen` fuera del vocabulario válido).

### POST `/api/movimientos/salidas/multiple` — registra una salida con varios productos · **`require_super_admin`**

```json
{
  "productos": [
    { "producto_codigo": "PROD-001", "cantidad": 15, "ubicacion": "A10-1" },
    { "producto_codigo": "PROD-002", "cantidad": 10, "ubicacion": "A10-2" }
  ],
  "motivo": "Salida combinada",
  "cliente_destino": "Cliente Y",
  "notas": null
}
```
A diferencia de la entrada múltiple, **`ubicacion` es obligatoria en cada item** — no hay
ubicación global de fallback. Respuesta: `MovimientoResponse` (201), modalidad `multiple`, con
`remision` propia. Errores: `PROD-002` (404, algún producto no existe), `MOV-002` (404, algún
item referencia una ubicación inexistente), `MOV-003` (422, stock físico insuficiente en
alguna ubicación).

### POST `/api/movimientos/salida-por-mercado` — registra la salida de un mercado predefinido · **`require_super_admin`**

```json
{
  "mercado_nombre": "Mercado Básico",
  "productos": [
    { "producto_codigo": "PROD-001", "ubicacion": "ALMACEN_GENERAL" },
    { "producto_codigo": "PROD-002", "ubicacion": "A10" }
  ],
  "cantidad": 3,                 // multiplicador — default 1
  "cliente_destino": "Cliente Y",
  "notas": null,
  "referencia": "REF-123"
}
```
Resuelve los productos del mercado predefinido y multiplica cada `producto_kit.cantidad` por
`cantidad`. Igual que en `/salidas/multiple`, **`ubicacion` es obligatoria en cada item de
`productos`** — cada producto del kit puede vivir en una ubicación física distinta, así que no
existe un único campo `ubicacion` global para todo el mercado (`MOV-009` si falta la de algún
producto del kit). Respuesta: `MovimientoResponse` (201), modalidad `mercado`, con
`nombre_mercado`/`referencia` poblados y `remision` propia. Errores: `MERC-002` (404, no
existe un mercado con ese nombre), `PROD-002` (404, algún producto del mercado ya no existe en
el catálogo), `MOV-009` (400, falta la ubicación de algún producto del kit en `productos`),
`MOV-002` (404, la ubicación indicada no existe para algún producto del mercado), `MOV-003`
(422, stock físico insuficiente en la ubicación indicada).

### POST `/api/movimientos/reservas/{session_id}/confirmar` — confirma una reserva (normal, kit o múltiple) · **`require_super_admin`**

Sin body. `cliente_destino`/`notas`/`kit_nombre`/`caso` de los movimientos creados vienen de
`reserva.datos_adicionales`, no del request. El backend detecta la modalidad solo — el
frontend no la elige.

```json
// Respuesta (201) — ConfirmacionReservaResponse
{
  "movimientos": [ /* MovimientoResponse[] — N items si es normal, 1 si es kit o múltiple */ ],
  "remision": "RM-001"   // compartida por todos los movimientos generados
}
```
Errores: `RES-002` (404, no existe una reserva para esa sesión), `MOV-004` (400, la reserva es
de una modalidad desconocida), `PROD-002` (404, algún item referencia un producto
inexistente), `MOV-002` (404, algún item referencia una ubicación inexistente), `MOV-003`
(422, stock físico insuficiente en alguna ubicación). Si cualquier item falla, **no se crea
ningún movimiento y la reserva no se borra** (transacción atómica).

### GET `/api/movimientos` — lista paginada, filtros combinables · `require_authenticated`

Query params (todos opcionales, se combinan con AND): `producto_codigo`, `tipo`
(`entrada`|`salida`|`creacion_ubicacion`|`transferencia_ubicacion`), `fecha_desde`,
`fecha_hasta` (ISO 8601), `motivo`, `remision`, `caso`, `origen_destino` (texto libre, busca
en proveedor **o** cliente), `pagina` (default 1), `limite` (default 20, máx 200).

### GET `/api/movimientos/exportar/excel` — exporta a `.xlsx` · `require_authenticated`

Query params: `fecha_desde`, `fecha_hasta`, `tipo` (los 4 valores válidos). Respuesta: archivo
binario
(`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), no JSON.

### GET `/api/movimientos/{id}/comprobante` — genera el PDF de una salida · `require_authenticated`

Funciona para las 4 modalidades de salida (individual, kit, múltiple, mercado). Respuesta:
archivo binario (`Content-Type: application/pdf`). Error: `MOV-005` (404, no existe una
salida con ese id).

### POST `/api/movimientos/{id}/pdf-firmado` — sube el PDF firmado a mano · `require_authenticated`

Body: `multipart/form-data`, campo `archivo` (el `.pdf`). Respuesta: `MovimientoResponse`
(200) con `pdf_nombre` poblado. Errores: `MOV-005` (404, no existe una salida con ese id),
`MOV-006` (400, el archivo subido no es un `.pdf`).

### GET `/api/movimientos/{id}/pdf-firmado` — descarga el PDF firmado subido · `require_authenticated`

Respuesta: archivo binario (`Content-Type: application/pdf`). Errores: `MOV-005` (404, no
existe una salida con ese id), `MOV-007` (404, la salida existe pero todavía no tiene un PDF
firmado subido).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `PROD-002` | 404 | No existe un producto con ese código | Revisar el selector de producto |
| `MOV-001` | 400 | Falta la ubicación al registrar una salida | No debería verse desde el frontend (el campo es obligatorio en el form) |
| `MOV-002` | 404 | El producto no tiene esa ubicación | Ofrecer las ubicaciones reales del producto (`GET /api/productos/{codigo}/ubicaciones`) |
| `MOV-003` | 422 | Stock físico insuficiente en esa ubicación | Mostrar `disponible` del error y sugerir bajar la cantidad |
| `MOV-004` | 400 | La reserva es de una modalidad desconocida (no normal/kit/múltiple) | Indicar datos corruptos — no debería verse en operación normal |
| `MOV-005` | 404 | No existe una salida con ese id | Revisar el id del movimiento |
| `MOV-006` | 400 | El archivo subido no es un `.pdf` | Pedir al usuario un archivo `.pdf` |
| `MOV-007` | 404 | La salida existe pero no tiene un PDF firmado subido todavía | Ofrecer el flujo de "subir PDF firmado" en vez de descarga |
| `MOV-008` | 400 | El movimiento (entrada múltiple, salida múltiple o mercado) no tiene productos | No debería verse desde el frontend (`productos` ya es obligatorio y no vacío en el form) |
| `MOV-009` | 400 | Falta la ubicación de algún producto del mercado en `/salida-por-mercado` | No debería verse desde el frontend (el form pide la ubicación de cada producto del kit antes de habilitar el envío) |
| `MERC-002` | 404 | No existe un mercado predefinido con ese nombre | Refrescar el selector de mercados (`GET /api/mercados-predefinidos`) |
| `RES-002` | 404 | No existe una reserva para esa sesión | Tratar como carrito vacío/ya confirmado |

## Notas de comportamiento

- `productos.stock_actual` **siempre se recalcula como la suma de todas las ubicaciones**, en
  la misma transacción Mongo que el movimiento — nunca un `$inc` suelto (a diferencia del
  legacy, que podía desincronizarse).
- La remisión (`RM-NNN`) se genera con un contador atómico (`find_one_and_update`/`$inc`) — no
  hay riesgo de dos salidas recibiendo el mismo número bajo concurrencia.
- Al confirmar una reserva, el stock de cada ubicación se descuenta **una sola vez** (el legacy
  tenía un bug real de doble descuento en este flujo — no se reprodujo).
- En modalidad kit, `numero_cajas` siempre es `0` — el legacy lo trackeaba por item pero ese
  dato no sobrevivió al modelo de `reservas` (y no aparecía poblado en los kits reales).
- El comprobante PDF **no se genera automáticamente al confirmar** una reserva — hay que
  pedirlo explícitamente vía `GET /{id}/comprobante` cuando se necesite.
- En la entrada múltiple, el item persistido siempre refleja la ubicación **real** donde se
  aplicó el stock (propia, o la global del request, o `ALMACEN_GENERAL`) — el legacy tenía un
  bug que podía mostrar `"ALMACEN_GENERAL"` aunque el stock se hubiera aplicado a otra
  ubicación. No se reprodujo.
- Las bitácoras de `ubicaciones` (`creacion_ubicacion`/`transferencia_ubicacion`) son
  puramente informativas — no representan una entrada o salida de inventario real, solo el
  registro de que se creó una ubicación o se redistribuyó stock entre dos. No suman/restan al
  total de `productos.stock_actual` por sí mismas (eso ya lo hizo `ubicaciones`).
- En modalidad `mercado`, `cantidad` en la respuesta es el **multiplicador de mercados**
  solicitado, no la suma de items — para ver cuánto se descontó de cada producto hay que mirar
  `productos[].cantidad` (ya multiplicado por el kit).
- `POST /salida-por-mercado` **no elige automáticamente una ubicación con stock suficiente** —
  exige una ubicación explícita por cada producto del kit en `productos` (no una única
  ubicación global, porque cada producto puede vivir en un lugar físico distinto). Es una
  desviación deliberada del legacy: la función que intentaba ese auto-pick
  (`get_ubicaciones_producto`) nunca existió realmente en el código legacy real, era un bug sin
  ejecutar en producción.
- `POST /salidas/multiple` exige **ubicación explícita en cada item** — a diferencia de la
  entrada múltiple, no hay ubicación global de fallback.
- ⚠️ **Fuera de alcance, sin construir**: confirmar varias reservas en un solo comprobante — el
  legacy nunca lo implementó, no hay comportamiento real que preservar. Se diseñaría de cero
  si en algún momento hay demanda real.
