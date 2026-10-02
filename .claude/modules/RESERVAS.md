# Módulo `reservas`

> Estado: **incremento 1 completo** (ajustar/consultar/eliminar + stock disponible).
> "Confirmar reserva" (convertirla en salida real) es responsabilidad de `movimientos`, que ya
> lo implementa para modalidad normal (incremento 2 de `movimientos`) — kit/múltiple
> pendientes. Ver `MIGRATION_PLAN.md` — es el módulo de mayor riesgo de lógica de todo el plan.

## Responsabilidad

Carrito de trabajo temporal por sesión (`session_id`): permite "apartar" stock de uno o más
productos/ubicaciones mientras se arma una salida, sin comprometerlo físicamente hasta que
`movimientos` confirme la operación.

## Entidades

- **`Reserva`** (`domain/entities/reserva.py`): `id`, `session_id` (único), `items:
  list[ItemReserva]`, `datos_adicionales` (dict libre, contexto para `movimientos`),
  `creado_por` (usuario dueño del carrito), `actualizado_por`, `ultima_actividad` (campo
  dedicado para el TTL, no reutiliza `creado_por.fecha`).
  - `crear()` — rechaza `items` vacío.
  - `aplicar_ajuste(producto_codigo, ubicacion, diferencia, actualizado_por)` — un item por
    llamada, delta con signo. Crea el item si `diferencia > 0` y no existía; lo elimina si
    la cantidad resultante es `<= 0`; no-op si se resta de un item inexistente.
  - Property `sin_items` — el service la usa para decidir si debe borrar el documento
    completo.
- **`ItemReserva`** (value object embebido): `producto_codigo`, `ubicacion`, `cantidad`. Sin
  `producto_nombre`/`stock_actual` cacheados — se resuelven en vivo si hace falta mostrarlos.

## Casos de uso (servicios)

| Servicio | Qué hace | Permiso |
|---|---|---|
| `AjustarReservaService` | Crea la reserva si no existe (solo con ajustes positivos) o aplica ajustes sobre la existente; borra el documento si queda sin items; valida stock disponible antes de aceptar un ajuste positivo | `require_authenticated` |
| `ObtenerReservaService` | Por `session_id`, sin restricción de dueño | `require_authenticated` |
| `EliminarReservaService` | Borra el carrito completo | **`require_super_admin`** |
| `CalcularStockDisponibleService` | `stock_fisico` − reservas activas de otras sesiones − reservas de la sesión actual | `require_authenticated` |

## Colecciones Mongo

- **`reservas_stock`** (no `reservas` — colisión con 3 reservas abandonadas reales del
  legacy). Índices: único en `session_id`, normal en `items.producto_codigo`, **TTL de 3
  días sobre `ultima_actividad`** (auto-expira carritos abandonados).

## Dependencias con otros módulos

Depende de `ubicaciones` (`UbicacionRepositoryPort`, solo lectura de `stock_fisico`). Es
dependido por `movimientos` (`ReservaRepositoryPort`, solo por puerto) para confirmar
reservas como salidas reales.

`ReservaRepositoryPort.actualizar`/`eliminar` aceptan un `uow: UnitOfWorkPort | None = None`
opcional (agregado durante el incremento 2 de `movimientos`, retrocompatible — los servicios
de este módulo no lo usan) para que borrar la reserva participe de la misma transacción que
el descuento de stock al confirmar.

## Flujos principales

1. **Armar el carrito**: `POST /{session_id}/ajustar` con ajustes de cantidad con signo
   (positivo = agregar, negativo = quitar). Si es la primera vez, crea la reserva.
2. **Consultar disponibilidad**: `GET /stock-disponible/{producto_codigo}/{ubicacion}`
   (opcionalmente con `?session_id=` para ver el desglose propio vs. de otros).
3. **Vaciar el carrito**: ajustar hasta cantidad 0 en todos los items → el documento se
   elimina solo. **`DELETE` (borrar todo de una) es exclusivo de `super_admin`.**

## Notas de comportamiento — decisión arquitectónica clave

**No hay ningún contador de "stock reservado" cacheado.** El legacy mantenía
`ubicaciones.stock_reservado` con `$inc`, pero ese contador se confirmó redundante y
corrupto (valores negativos reales) — el cálculo real de disponibilidad siempre se hizo en
vivo. Este módulo replica *ese* comportamiento real, no el contador cacheado. Consecuencia
directa: el TTL de reservas abandonadas no deja nada huérfano en otra colección, porque no
hay nada más que sincronizar.

`ubicaciones.stock_reservado` (campo modelado en el módulo `ubicaciones`) queda confirmado
como no usado por ningún service — es deuda documentada, no un bug de esta implementación.

## Modelo de permisos (aplica también a `movimientos`, a futuro)

Confirmado con el desarrollador: `operativo` hace reservas y "entradas previas"; `admin` es
de solo lectura (inventario, productos, informes); **`super_admin` es el único que confirma
entradas y reservas (que se vuelven salidas) y el único que puede eliminar una reserva**.
Es jerárquico sobre los 3 roles de `auth`, no cambia el criterio de `productos`/
`ubicaciones`/`mercados_predefinidos` (que siguen con `require_authenticated` genérico).

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `reservas`": el hallazgo de los dos mecanismos
paralelos de stock reservado en el legacy, la unificación de `guardar_reserva`/
`ajustar_reserva` en un solo `AjustarReservaService`, y el bug real de mapeo DTO↔schema
encontrado y corregido durante la verificación end-to-end.
