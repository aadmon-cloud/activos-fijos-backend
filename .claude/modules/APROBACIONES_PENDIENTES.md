# Módulo `aprobaciones_pendientes`

> Estado: **CERRADO — 1/1 incremento completo**. Ver `MIGRATION_PLAN.md` — a diferencia del
> resto del plan, este módulo no migra una capacidad funcional del legacy en su parte central:
> "confirmar" nunca aplicó el movimiento real ahí (stub roto, nunca ejecutado en producción).
> Se diseñó desde una Fase 0 explícita con el desarrollador, usando el legacy solo como
> referencia de forma de datos y reglas de autorización.

## Responsabilidad

Permitir que cualquier usuario autenticado (no solo `super_admin`) proponga una entrada o
salida de inventario que queda en estado `pendiente` hasta que un **`super_admin`** la
confirme (generando el `Movimiento` real vía `movimientos`) o alguien autorizado la elimine.
Ningún otro rol, ni siquiera `admin`, puede confirmar — un no-`super_admin` solo puede dejar
la propuesta en estado "pre" (`pendiente`).

## Entidades

- **`MovimientoPendiente`** (`domain/entities/movimiento_pendiente.py`): `id`,
  `tipo_propuesto` (`entrada`|`entrada_multiple`|`salida`|`salida_multiple` — unifica los
  `EntradaPendiente`/`SalidaPendiente` duplicados del legacy en una sola entidad), `payload`
  (dict — mismos campos que el `Input` DTO de `movimientos` correspondiente, validado en la
  capa de aplicación, no en el dominio; mismo criterio que `reservas.datos_adicionales`),
  `estado` (`pendiente`|`confirmada`), `movimiento_id` (referencia al `Movimiento` real, solo
  tras confirmar), `creado_por` (quien propone), `confirmado_por` (quien confirma — queda
  como autor del `Movimiento` real, no quien propuso).
  - `proponer(tipo_propuesto, payload, creado_por)` — factory, `estado="pendiente"`.
  - `.confirmar(movimiento_id, confirmado_por)` — devuelve una nueva instancia
    `estado="confirmada"`; lanza `MovimientoPendienteYaConfirmadoError` si ya no está
    `pendiente`.
  - `.exigir_eliminable()` — mismo chequeo, usado antes de eliminar (no se borra el historial
    de una ya confirmada).
  - `.pertenece_a(id_persona)` — pura comparación de identidad; el dominio no conoce roles,
    eso es responsabilidad de la capa de aplicación.

## Casos de uso (servicios)

| Servicio | Qué hace | Permiso |
|---|---|---|
| `ProponerEntradaService` / `ProponerEntradaMultipleService` / `ProponerSalidaService` / `ProponerSalidaMultipleService` | Reciben el mismo `Input` DTO que su equivalente de `movimientos` (reutilizado, sin duplicar validación), envuelven en `MovimientoPendiente.proponer(...)` y persisten | `require_authenticated` |
| `ListarMovimientosPendientesService` | `super_admin` ve todas; el resto solo las propias — el filtro de dueño lo fuerza el servicio según el rol, nunca confía en lo que traiga el request | `require_authenticated` |
| `EliminarMovimientoPendienteService` | 404 si no existe, 403 si no es dueño ni `super_admin`, 409 si ya fue confirmada (se preserva su historial) | `require_authenticated` (+ chequeo de dueño interno) |
| `EliminarMovimientosPendientesMultiplesService` | Best-effort sobre una lista de ids, sin chequeo de dueño individual (mismo alcance que el legacy); a diferencia del legacy, no elimina las ya confirmadas | **`require_super_admin`** |
| `ConfirmarMovimientoPendienteService` | **Dispatcher**: reconstruye el `Input` real de `movimientos` desde `payload` según `tipo_propuesto`, y dentro de **una única transacción** aplica el movimiento real (vía `EjecutorDeMovimientosPort`) y actualiza la propuesta (`estado`, `movimiento_id`, `confirmado_por`) | **`require_super_admin`** |

## Colección Mongo

- **`movimientos_pendientes`** (nueva, aislada — no colisiona con las legacy
  `entradas_pendientes`/`salidas_pendientes`, que siguen existiendo con datos reales y nunca se
  tocan). Índices: `estado`, compuesto `(creado_por.id_persona, estado)` (el caso más común:
  "mis propuestas sin confirmar"), `tipo_propuesto`, `creado_por.fecha` desc.

## Dependencias con otros módulos

Depende de `movimientos` vía `EjecutorDeMovimientosPort` — puerto **propiedad de
`movimientos`** (no de `aprobaciones_pendientes`, a diferencia del patrón de inversión de
dependencias usado en la bitácora de `ubicaciones`), ya que no hay riesgo de ciclo:
`movimientos` nunca necesita llamar de vuelta a `aprobaciones_pendientes`. El adaptador
concreto (`MovimientosEjecutorAdapter`) vive en
`modules/movimientos/infrastructure/aprobaciones/` y envuelve los 4 servicios de registro
directo ya existentes (`RegistrarEntradaService`, `RegistrarEntradaMultipleService`,
`RegistrarSalidaService`, `RegistrarSalidaMultipleService`). El *provider* de FastAPI
(`get_ejecutor_de_movimientos`) se importa desde
`modules/movimientos/infrastructure/api/dependencies.py`, mismo patrón de cableado cruzado ya
usado en el resto del plan.

## Flujos principales

1. **Proponer**: `POST /entradas`, `/entradas/multiple`, `/salidas`, `/salidas/multiple` →
   cualquier autenticado guarda una propuesta en estado `pendiente`, sin tocar stock ni crear
   ningún `Movimiento` todavía.
2. **Listar**: `GET ""` con filtros (`estado`, `tipo_propuesto`) y paginación — visibilidad
   forzada por rol, no por lo que pida el cliente.
3. **Eliminar individual**: `DELETE /{id}` — el dueño o un `super_admin`; rechaza si ya fue
   confirmada.
4. **Eliminar en lote**: `DELETE /eliminar-multiples` — exclusivo `super_admin`, best-effort.
5. **Confirmar**: `POST /{id}/confirmar` → exclusivo `super_admin`. Dentro de una única
   transacción: reconstruye el `Input` real de `movimientos` según `tipo_propuesto`, invoca el
   servicio correspondiente vía `EjecutorDeMovimientosPort` (crea el `Movimiento` real,
   descuenta/suma stock), y marca la propuesta como `confirmada` con `movimiento_id` y
   `confirmado_por`. Responde con el `MovimientoResponse` real (mismo shape que
   `GET /api/movimientos/{id}`).

## Notas de comportamiento

- **"Confirmar" en el legacy nunca aplicaba el movimiento real** — verificado leyendo el
  código fuente: la variable `datos` se leía de Mongo pero nunca se usaba; el endpoint solo
  hacía `update_one({"estado": "confirmada"})`. Las líneas `# Llamar a tu función de entrada
  múltiple` / `# await crud.crear_entrada_multiple(db, ...)` estaban comentadas y jamás se
  ejecutaron. Este módulo corrige ese stub — no lo reproduce.
- **Solo `super_admin` puede confirmar** (entradas o salidas), decisión explícita del
  desarrollador — ni siquiera `admin` tiene ese privilegio. Cualquier otro rol solo puede
  proponer (dejarla en estado "pre"/`pendiente`).
- **El autor del `Movimiento` generado es quien confirma, no quien propuso** — el
  `super_admin` que ejecuta la acción real de mover stock queda como `creado_por` del
  movimiento; `confirmado_por` en la propuesta registra la misma persona.
- **Atomicidad entre "crear el movimiento real" y "marcar la pendiente como confirmada"**: los
  4 servicios de `movimientos` fueron reabiertos para aceptar un `uow` externo opcional en
  `ejecutar()` — sin esto, un fallo entre ambos pasos podría dejar un `Movimiento` real
  aplicado con la pendiente todavía en `estado="pendiente"`, permitiendo un reintento que
  generara un movimiento duplicado. Con el `uow` compartido, ambos pasos son atómicos.
  Extensión no disruptiva: ningún llamador previo pasa `uow`, comportamiento existente
  intacto (4 tests de regresión lo confirman).
- **Una propuesta ya confirmada no se puede eliminar** (individual ni en lote) — se preserva
  su historial (`movimiento_id`, `confirmado_por`) en vez de borrarla, a diferencia del legacy
  que sí permitía borrar cualquier documento sin chequear su estado.
- **Los 4 tipos proponibles reutilizan directamente los `Input` DTO de `movimientos`**
  (`RegistrarEntradaInput`, etc.) tanto para proponer (el payload persistido es
  `entrada.model_dump()`) como para confirmar (se reconstruye `Input(**payload)`) — evita
  duplicar reglas de validación entre ambos módulos.
- **Fuera de alcance**: `salida_por_mercado` (sin precedente en el flujo legacy de pendientes)
  y confirmar reservas (mecanismo ya resuelto en `reservas`/`movimientos`, sin relación con
  este módulo).

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `aprobaciones_pendientes`": Fase 0 completa con las
5 decisiones acordadas con el desarrollador (comportamiento real de "confirmar", exclusividad
de `super_admin`, autoría del movimiento, unificación de entidad, atomicidad vía reapertura de
`movimientos`).

## Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

`super_admin` + 2 operativos + 2 productos/ubicaciones de prueba → cada operativo propone
entrada/salida/entrada_multiple/salida_multiple → listar como operativo solo muestra las
propias, listar como super_admin muestra las de todos → confirmar con operativo (403) →
confirmar entrada con super_admin (201, `Movimiento` real creado, stock recalculado, referencia
completada en la propuesta) → confirmar de nuevo la misma (409, `APR-002`) → confirmar
`salida_multiple` (201, cubre el otro extremo del dispatcher) → confirmar inexistente (404,
`APR-001`) → eliminar la propuesta de otro sin ser dueño ni super_admin (403, `APR-003`) → el
dueño elimina la propia (204) → eliminar una ya confirmada (409, `APR-002`) → eliminar
inexistente (404, `APR-001`) → `eliminar-multiples` con operativo (403), con super_admin sobre
pendiente/confirmada/inexistente mezcladas (200, solo elimina la real).

`movimientos`/`entradas_pendientes`/`salidas_pendientes` (legacy) verificados intactos antes y
después. Datos de prueba eliminados. Suite completa: **320/320 tests verdes** (280 previos +
8 en la suite de `movimientos` por la reapertura — 4 de regresión del `uow` opcional y 4 del
adaptador `MovimientosEjecutorAdapter` — + 32 nuevos en este módulo: 6 de dominio, 19 de
aplicación, 7 del repositorio Mongo).
