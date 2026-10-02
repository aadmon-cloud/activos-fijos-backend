# API — Módulo de Productos

> Para estadísticas agregadas (bajo stock, valor total, dashboard), ver
> `docs/api/INVENTARIO_REPORTES.md`.

**Base:** `/api/productos` · **Auth:** Bearer token (solo en escritura)

Catálogo maestro de productos. La lectura (listar, obtener, buscar) es pública; crear,
editar y eliminar requieren autenticación.

---

## 1. Convenciones de respuesta

Mismo envelope de error y tabla categoría→HTTP que `auth` (ver `docs/api/AUTH.md`, sección 1).

**Paginación**: `{ "resultado": [...], "pagina_actual": 1, "elementos_por_pagina": 10, "total_elementos": 42, "total_paginas": 5 }`.

## 2. Tipos y enums

```json
// ProductoResponse
{
  "id": "...", "codigo": "PROD-20260101-ABC123", "nombre": "Laptop HP",
  "descripcion": null, "categoria": "Electrónica",
  "stock_minimo": 5, "stock_actual": 40, "precio_unitario": 999.99, "imagen_url": null
}
```

`stock_actual` es de **solo lectura** — se recalcula desde `ubicaciones`, nunca se envía en creación/edición.

## 3. Flujos

- **Catálogo público**: cualquier visitante (sin login) puede listar, obtener por código o buscar.
- **Alta de producto**: `POST` con auth. Si no se manda `codigo`, se autogenera.
- ⚠️ El `codigo` es inmutable una vez creado — no hay endpoint para cambiarlo.

## 4. Endpoints

### GET `/api/productos` — lista paginada · público

Query: `?pagina=1&limite=10`.

### GET `/api/productos/buscar` — búsqueda de texto · público

Query: `?q=laptop` (busca en nombre, código y descripción, case-insensitive).

### GET `/api/productos/{codigo}` — obtiene por código · público

Error: `PROD-002` (404).

### POST `/api/productos` — crea · `require_authenticated`

```json
{ "codigo": null, "nombre": "Laptop HP", "descripcion": "...", "categoria": "Electrónica", "stock_minimo": 5, "precio_unitario": 999.99 }
```
`codigo` opcional (se autogenera). Error: `PROD-001` (409, código duplicado).

### PUT `/api/productos/{codigo}` — update parcial · `require_authenticated`

Mismo shape que crear, todo opcional. No acepta `stock_actual` ni `imagen_url`. Error: `PROD-002` (404).

### DELETE `/api/productos/{codigo}` — elimina · `require_authenticated`

Error: `PROD-002` (404).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `PROD-001` | 409 | El código ya está registrado | Sugerir dejar el campo vacío para autogenerar |
| `PROD-002` | 404 | No existe un producto con ese código | Refrescar el listado/redirigir a la búsqueda |

## Notas de comportamiento

- `stock_actual` nace en `0` y solo cambia cuando se crean/editan/eliminan ubicaciones de ese producto (ver `docs/api/UBICACIONES.md`) — no lo actualiza este módulo directamente.
- La búsqueda es sobre `$regex`, no full-text search — soporta substrings parciales, no ranking por relevancia.
- Fuera de alcance de este incremento: carga masiva por Excel, código de barras/QR, imagen de producto.
