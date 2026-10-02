# API — Módulo de Mercados Predefinidos

**Base:** `/api/mercados-predefinidos` · **Auth:** Bearer token (solo en escritura)

Catálogo de "kits" de productos predefinidos (ej. `KIT_BASICO`) para agilizar salidas
masivas. Lectura pública, escritura autenticada.

---

## 1. Convenciones de respuesta

Mismo envelope de error que `auth` (ver `docs/api/AUTH.md`, sección 1). Sin paginación.

## 2. Tipos y enums

```json
// MercadoPredefinidoResponse
{
  "id": "...", "nombre": "KIT_BASICO", "descripcion": "Kit básico", "activo": true,
  "productos": [
    { "producto_id": "100", "cantidad": 2, "producto_nombre": "ARROZ" },
    { "producto_id": "200", "cantidad": 1, "producto_nombre": "ACEITE" }
  ]
}
```

⚠️ `producto_nombre` lo resuelve el servidor al momento de crear/editar — no lo confía del cliente. Puede quedar desactualizado si el producto cambia de nombre después (se re-sincroniza recién en la próxima edición del kit).

## 3. Flujos

- **Armar un kit**: `POST` con la lista de `{producto_id, cantidad}` — el servidor completa `producto_nombre`.
- **Desactivar sin borrar**: `PUT` con `{"activo": false}` — el kit deja de aparecer en el listado por defecto pero no se elimina.
- ⚠️ `nombre` no se puede cambiar una vez creado el kit.

## 4. Endpoints

### GET `/api/mercados-predefinidos` — lista · público

Query: `?solo_activos=true` (default `true`).

### GET `/api/mercados-predefinidos/{nombre}` — obtiene por nombre · público

Error: `MERC-002` (404).

### POST `/api/mercados-predefinidos` — crea · `require_authenticated`

```json
{ "nombre": "KIT_BASICO", "descripcion": "...", "productos": [{ "producto_id": "100", "cantidad": 2 }] }
```
Errores: `MERC-001` (409, nombre duplicado), `PROD-002` (404, algún `producto_id` no existe).

### PUT `/api/mercados-predefinidos/{nombre}` — update parcial · `require_authenticated`

```json
{ "descripcion": "...", "productos": [...], "activo": false }
```
Si se manda `productos`, reemplaza la lista completa (no es un merge) y re-resuelve todos los nombres.
Errores: `MERC-002` (404), `PROD-002` (404, algún producto nuevo no existe).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `MERC-001` | 409 | Ya existe un kit con ese nombre | Sugerir editar el existente |
| `MERC-002` | 404 | No existe un kit con ese nombre | Refrescar el listado |
| `MERC-003` | 400 | El kit debe tener al menos un producto | Bloquear el submit si la lista queda vacía |

## Notas de comportamiento

- `PUT` con `productos` reemplaza la lista entera — para agregar un producto hay que mandar la lista completa (existente + nuevo), no solo el nuevo.
- Usar un kit para generar una salida real vive en `movimientos`:
  `POST /api/movimientos/salida-por-mercado` (ver `docs/api/MOVIMIENTOS.md`) consume este
  módulo **solo en lectura**, vía `MercadoPredefinidoRepositoryPort`, para resolver
  `producto_id`/`cantidad` de cada item del kit y multiplicarlos por la cantidad de mercados
  solicitada. Nunca escribe en `catalogo_mercados_predefinidos`.
