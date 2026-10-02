# Módulo `ubicaciones`

> Estado: **incremento 1 completo** (CRUD + transferencia), **reabierto en el incremento 5 de
> `movimientos`** para emitir bitácora (ver más abajo). Ver `MIGRATION_PLAN.md` — es el módulo
> de mayor riesgo de consistencia de todo el plan.

## Responsabilidad

Registrar y mantener el stock físico de cada producto distribuido por ubicación física
(bodega/anaquel/etc.). Es la **fuente de verdad** del stock — `productos.stock_actual` es
una proyección recalculada desde acá, nunca al revés.

## Entidades

- **`Ubicacion`** (`domain/entities/ubicacion.py`): `id`, `producto_codigo`, `ubicacion`
  (nombre de la ubicación física, único junto con `producto_codigo`), `stock_fisico`,
  `stock_reservado` (**campo sin uso** — ver Notas), `creado_por`, `actualizado_por`.
  - `crear()`, `actualizar_stock_fisico()`.
  - Property `stock_disponible` = `max(0, stock_fisico - stock_reservado)` — no es la que
    usa `reservas` para su cálculo real (ver Notas).

## Casos de uso (servicios)

| Servicio | Qué hace | Usa `MongoUnitOfWork` |
|---|---|---|
| `CrearUbicacionService` | Crea ubicación, recalcula `productos.stock_actual`, deja bitácora en `movimientos` (`creacion_ubicacion`) | Sí |
| `ActualizarUbicacionService` | Cambia `stock_fisico`, recalcula `stock_actual` | Sí |
| `EliminarUbicacionService` | Elimina, recalcula `stock_actual` | Sí |
| `TransferirStockService` | Mueve stock entre 2 ubicaciones del mismo producto (crea destino si no existe), deja bitácora en `movimientos` (`transferencia_ubicacion`) | Sí |
| `ObtenerProductoConUbicacionesService` | Lectura: producto + todas sus ubicaciones | No |

`ActualizarUbicacionService`/`EliminarUbicacionService` **no** dejan bitácora — decisión
explícita del incremento 5 de `movimientos` (esos dos tipos no tienen precedente en los datos
reales de `inventario_db`, a diferencia de creación/transferencia).

## Colecciones Mongo

- **`stock_ubicaciones`** (no `ubicaciones` — colisión con datos reales corruptos del
  legacy, varios con `stock_fisico`/`stock_reservado` negativos). Índice único compuesto:
  `(producto_codigo, ubicacion)`.

## Dependencias con otros módulos

Depende de `productos` (`ProductoRepositoryPort`, para leer y recalcular `stock_actual`).
Expone `UbicacionRepositoryPort`, consumido por `reservas` (lectura de `stock_fisico`) y por
`movimientos` (lectura/escritura, para entradas/salidas/confirmaciones).

**Expone además `RegistradorDeMovimientosPort`** (`application/ports/`, propiedad de este
módulo) — `CrearUbicacionService`/`TransferirStockService` lo llaman para dejar bitácora en
`movimientos`, pero `ubicaciones/application` **no importa nada de `movimientos`**: el
adaptador concreto (`MovimientosRegistradorDeMovimientosAdapter`) vive en `movimientos` y se
cablea únicamente en `modules/ubicaciones/infrastructure/api/dependencies.py`, que importa el
*provider* de dependencia desde `modules/movimientos/infrastructure/api/dependencies.py`.
Inversión de dependencias deliberada — evita el ciclo `movimientos↔ubicaciones` que se habría
formado si `ubicaciones` dependiera directamente de algo de `movimientos`. Ver
`MIGRATION_PLAN.md`, incremento 5 de `movimientos`.

## Flujos principales

1. **Crear/actualizar/eliminar ubicación** → siempre recalcula `productos.stock_actual`
   como la suma de `stock_fisico` de todas las ubicaciones del producto, dentro de una
   transacción Mongo real (`MongoUnitOfWork`).
2. **Transferir stock**: resta en origen, suma en destino (lo crea si no existe) — no toca
   `productos.stock_actual` porque el total no cambia, solo se redistribuye.

## Notas de comportamiento

- **`stock_reservado` está modelado pero sin ningún service que lo escriba.** El módulo
  `reservas` (construido después) decidió calcular disponibilidad en vivo agregando
  reservas activas, en vez de mantener este contador — que además se confirmó corrupto en
  los datos reales del legacy. Este campo queda como posible deuda a limpiar más adelante,
  no se está usando activamente.
- No hay techo de "stock máximo" al crear/actualizar una ubicación — cualquier
  `stock_fisico >= 0` es válido (ver decisión Fase 0 en `MIGRATION_PLAN.md`: el techo del
  legacy asumía un `stock_actual` independiente que hoy no existe sin `movimientos`).
- Rutas anidadas bajo `/api/productos/{codigo}/ubicaciones/...`, no bajo un prefijo propio.

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `ubicaciones`": el hallazgo del bug
`crear_movimiento_ubicacion` del legacy (crashea después de insertar), los datos reales con
stock negativo, y la conversión del servidor Mongo a replica set de un nodo (necesaria para
que `MongoUnitOfWork` funcionara). Ver también la sección "Módulo `movimientos`", incremento
5, para el diseño completo de la bitácora y el patrón de inversión de dependencias.
