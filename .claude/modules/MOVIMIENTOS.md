# Módulo `movimientos`

> Estado: **CERRADO — 6/6 incrementos completos** (movimiento individual + confirmar reserva
> normal/kit/múltiple + comprobante PDF + entrada múltiple directa + bitácora de `ubicaciones`
> + salida múltiple/por mercado directas). Ver `MIGRATION_PLAN.md` — fue el módulo de mayor
> riesgo y el más grande de todo el plan; se construyó en 6 incrementos, priorizados por uso
> real verificado contra `inventario_db` (23/58 movimientos reales son confirmaciones de kit,
> 3/58 entrada múltiple, 0/58 salida múltiple o por mercado). Única deuda documentada sin
> construir: "confirmar varias reservas en un comprobante" (sin demanda real hoy).

## Responsabilidad

Registrar toda entrada y salida de inventario, siendo (junto con `ubicaciones`) la única vía
legítima de alterar `productos.stock_actual`. Cubre movimiento individual, confirmación de
reservas en sus 3 modalidades (normal/kit/múltiple), comprobante PDF, entrada múltiple directa,
bitácora de creación/transferencia de ubicaciones, y salida múltiple/por mercado directas.

## Entidades

- **`Movimiento`** (`domain/entities/movimiento.py`): `id`, `tipo`
  (`entrada`|`salida`|`creacion_ubicacion`|`transferencia_ubicacion`), `modalidad`
  (`individual`|`kit`|`multiple`|`entrada_multiple`|`mercado` — las 5 modalidades ya tienen
  servicio real), `producto_codigo`/`producto_nombre` (desnormalizado, solo `individual`),
  `cantidad`, campos de contexto (`motivo`, `tipo_origen`, `origen_nombre`, `cliente_destino`,
  `ubicacion`, `ubicacion_origen`, `ubicacion_destino`, `notas`, `remision`, `caso`,
  `referencia`, `numero_cajas`, `kit_nombre`, `nombre_mercado`),
  `productos: list[ItemMovimiento]` (poblado en `kit`, `entrada_multiple`, `multiple` y
  `mercado`), `pdf_firmado`/`pdf_nombre`, `creado_por`, `actualizado_por`.
  - `registrar_entrada(...)` — `tipo="entrada"`, `remision=None` siempre, `ubicacion` default
    `"ALMACEN_GENERAL"` si no se especifica.
  - `registrar_salida(...)` — `tipo="salida"`, `modalidad="individual"`, rechaza `ubicacion`
    vacío (invariante de negocio, no solo de formato).
  - `registrar_kit(...)` — `tipo="salida"`, `modalidad="kit"`, **una sola salida por
    confirmación** (`cantidad=1` fijo, representa "1 kit"), `numero_cajas=0` siempre (ver
    Notas de comportamiento), `motivo="Salida de Kit"` fijo.
  - `registrar_entrada_multiple(...)` — `tipo="entrada"`, `modalidad="entrada_multiple"`,
    **una sola entrada** con `cantidad` = suma de items, `motivo = tipo_origen.capitalize()`,
    rechaza lista de productos vacía (`MOV-008`).
  - `registrar_multiple(...)` — `tipo="salida"`, `modalidad="multiple"`, `cantidad=1` fijo,
    `numero_cajas=0`, sin `kit_nombre`; usada tanto por confirmar reserva múltiple como por
    salida múltiple directa. Rechaza lista de productos vacía (`MOV-008`).
  - `registrar_mercado(...)` — `tipo="salida"`, `modalidad="mercado"`, `motivo` derivado
    (`"Salida de {nombre_mercado}"`), guarda `nombre_mercado`/`referencia`, `cantidad` es el
    multiplicador de mercados solicitado (no la suma de items). Rechaza lista de productos
    vacía (`MOV-008`).
  - `registrar_creacion_ubicacion(...)`/`registrar_transferencia_ubicacion(...)` — registros
    puramente históricos (no alteran stock; eso ya lo hizo `ubicaciones`), disparados desde el
    módulo `ubicaciones` vía `RegistradorDeMovimientosPort`.
  - `adjuntar_pdf_firmado(pdf_ruta, pdf_nombre, actualizado_por)` — único caso de update sobre
    un movimiento ya creado.
- **`ItemMovimiento`** (value object embebido): `producto_codigo`, `producto_nombre`,
  `cantidad`, `ubicacion`. Poblado en modalidad `kit`, `entrada_multiple`, `multiple` y
  `mercado` (uno por producto del kit/entrada/salida/mercado, con la ubicación real).

Reemplaza los 4 booleans no excluyentes del legacy (`es_kit`/`es_multiple`/
`es_entrada_multiple`/`es_kit_mercado`) por el campo `modalidad`, decisión aprobada en Fase 1.

## Casos de uso (servicios)

| Servicio | Qué hace | Permiso | Usa `MongoUnitOfWork` |
|---|---|---|---|
| `RegistrarEntradaService` | Suma stock en la ubicación (crea si no existía), recalcula `productos.stock_actual` como la suma de todas las ubicaciones, crea el movimiento | **`require_super_admin`** (revertido post-cierre — ver nota al final) | Sí |
| `RegistrarSalidaService` | Valida stock físico en la ubicación (única fuente de verdad — ya no se revalida el total denormalizado), genera remisión, descuenta stock, recalcula `stock_actual`, crea el movimiento | **`require_super_admin`** | Sí |
| `ListarMovimientosService` | Filtros combinables (producto, tipo, fecha, motivo, remisión, caso, texto libre proveedor/cliente) + paginación | `require_authenticated` | No |
| `ExportarMovimientosExcelService` | Devuelve movimientos filtrados sin paginar (fecha/tipo); la construcción del `.xlsx` es un adaptador de infraestructura, no del servicio | `require_authenticated` | No |
| `ConfirmarReservaService` | **Dispatcher**: lee la reserva una vez, detecta modalidad, delega a la estrategia normal/kit/múltiple correspondiente | **`require_super_admin`** | (delega) |
| `ConfirmarReservaNormalService` | Estrategia normal: una remisión compartida, un `Movimiento` por item, descuenta stock una sola vez (corrige el doble descuento del legacy), recalcula `stock_actual`, borra la reserva | (llamado por el dispatcher) | Sí |
| `ConfirmarReservaKitService` | Estrategia kit: **un solo** `Movimiento` con todos los productos embebidos, una remisión propia, descuenta stock de cada ubicación, recalcula `stock_actual`, borra la reserva | (llamado por el dispatcher) | Sí |
| `ConfirmarReservaMultipleService` | Estrategia múltiple: igual forma que la de kit, pero sin `kit_nombre` y con motivo fijo `"Entrega de Ayudas/Unidades"` | (llamado por el dispatcher) | Sí |
| `GenerarComprobantePdfService` | Genera el PDF de una salida ya registrada (individual, kit, múltiple o mercado) a demanda — no se genera automáticamente al confirmar/registrar | `require_authenticated` | No |
| `SubirPdfFirmadoService` | Sube el PDF firmado manualmente para una salida existente, lo guarda vía `StorageRepositoryPort` y actualiza el movimiento | `require_authenticated` | No |
| `ObtenerPdfFirmadoService` | Descarga el PDF firmado ya subido | `require_authenticated` | No |
| `RegistrarEntradaMultipleService` | Una sola entrada con varios productos, cada uno con su propia ubicación (o la global del request, o `ALMACEN_GENERAL`); recalcula `stock_actual` de cada producto afectado | **`require_super_admin`** (revertido post-cierre — ver nota al final) | Sí |
| `RegistrarSalidaMultipleService` | Una sola salida con varios productos, **cada uno con su propia ubicación obligatoria** (sin fallback a una global); valida stock y recalcula `stock_actual` por producto | **`require_super_admin`** | Sí |
| `RegistrarSalidaPorMercadoService` | Resuelve los productos de un `MercadoPredefinido` (solo lectura vía `MercadoPredefinidoRepositoryPort`), multiplica cada cantidad por el multiplicador solicitado, exige **una ubicación explícita por producto** del kit (revertido post-cierre — ver nota al final de este documento: un mercado real con productos en ubicaciones distintas no podía venderse con una única ubicación global) | **`require_super_admin`** | Sí |

Registro directo (entrada o salida, individual o múltiple) es **exclusivo `super_admin`**
(decisión revertida post-cierre — ver nota al final: la decisión original de Fase 0 permitía
`operativo`/`admin` registrar entradas directas, pero el desarrollador pidió unificar el
criterio con salidas: cualquier rol no-`super_admin` propone vía `aprobaciones_pendientes`,
nunca aplica un movimiento directo). Los servicios de PDF (generar/subir/descargar) solo requieren
autenticación — no son la acción que mueve stock.

La bitácora de `ubicaciones` **no es un servicio de `movimientos`** — la disparan
`CrearUbicacionService`/`TransferirStockService` (módulo `ubicaciones`) a través de
`RegistradorDeMovimientosPort`; el permiso aplicable es el de esos endpoints
(`require_authenticated`, ya vigente en `ubicaciones`), no uno nuevo.

## Colecciones Mongo

- **`registro_movimientos`** (no `movimientos` — colisión con 58 movimientos reales del
  legacy). Modelada completa desde ya (incluye campos de los incrementos 2-6 sin código que
  los use todavía, mismo patrón que `auth`/`productos`). Índices: `producto_codigo`,
  `productos.producto_codigo` (para cuando existan modalidades multi-producto),
  `creado_por.fecha` desc, `tipo`, compuestos `fecha+tipo` y `producto+fecha`, `remision` y
  `caso` (ambos sparse).
- **`contadores_movimientos`** (no `contadores` — colisión con el contador de remisión real
  del legacy, en `RM-023`). Documento `{nombre, prefijo, ultimo_numero}`, único en `nombre`.

## Dependencias con otros módulos

Depende de `productos` (`ProductoRepositoryPort`, para leer y recalcular `stock_actual`),
`ubicaciones` (`UbicacionRepositoryPort`, para leer/crear/actualizar stock físico), `reservas`
(`ReservaRepositoryPort`, para leer y borrar la reserva confirmada) y `mercados_predefinidos`
(`MercadoPredefinidoRepositoryPort`, **solo lectura**, para resolver los productos de un kit
predefinido en `RegistrarSalidaPorMercadoService`). Los cuatro consumidos solo por puerto,
nunca por repositorio concreto.

**Relación inversa con `ubicaciones`** (incremento 5): `ubicaciones` define y posee
`RegistradorDeMovimientosPort`; `movimientos` provee el adaptador concreto
(`MovimientosRegistradorDeMovimientosAdapter`, en `infrastructure/ubicaciones/`). El cableado
cruzado ocurre únicamente en `modules/ubicaciones/infrastructure/api/dependencies.py` (importa
el *provider* desde `modules/movimientos/infrastructure/api/dependencies.py`) — ningún módulo
importa el código de dominio/aplicación del otro. Esto evita el ciclo `movimientos↔ubicaciones`
que se habría formado si `ubicaciones` dependiera directamente del puerto de `movimientos`.

**Consumido por `aprobaciones_pendientes`** (módulo posterior, ver su propia documentación):
vía `EjecutorDeMovimientosPort` — a diferencia de `RegistradorDeMovimientosPort`, este puerto
es **propiedad de `movimientos`** (no del consumidor), porque no hay riesgo de ciclo:
`movimientos` nunca necesita llamar de vuelta a `aprobaciones_pendientes`. Esto motivó
reabrir los 4 servicios de registro directo para aceptar un `uow` externo opcional en
`ejecutar()` (no disruptivo — ningún llamador previo lo pasa).

**Consumido por `inventario_reportes`** (último módulo del plan): solo lectura, directamente
vía `MovimientoRepositoryPort.listar()` (sin cambios en el puerto) — reutilizado tanto para
"últimos 10 movimientos" como para el conteo de "movimientos de hoy" (con `fecha_desde` y
descartando la lista, solo se usa el `total_elementos`).

## Flujos principales

1. **Entrada individual**: `POST /entradas` → crea/suma ubicación → recalcula `stock_actual`
   como suma de ubicaciones → crea el movimiento. Todo en una transacción.
2. **Salida individual**: `POST /salidas` → valida stock en la ubicación → genera remisión
   (atómica, `find_one_and_update`/`$inc`, dentro de la misma transacción) → descuenta →
   recalcula `stock_actual` → crea el movimiento.
3. **Confirmar reserva**: `POST /reservas/{session_id}/confirmar` → `ConfirmarReservaService`
   obtiene la reserva (404 si no existe), detecta la modalidad (heurística sobre
   `datos_adicionales.tipo`/`kitNombre`) y delega:
   - **Normal**: por cada item, valida stock, descuenta, recalcula `stock_actual`, crea un
     `Movimiento` — una remisión **compartida** por todos los items.
   - **Kit**: un solo `Movimiento` con `productos` embebidos, una remisión propia, descuenta
     stock de cada ubicación referenciada.
   - **Múltiple**: igual forma que kit, sin `kit_nombre`, motivo fijo `"Entrega de
     Ayudas/Unidades"`.
   - **Cualquier otra modalidad**: `MOV-004` (`ModalidadReservaNoSoportadaError`).
   Todo dentro de una única transacción por confirmación — si un item falla, ningún item
   queda aplicado y la reserva no se borra.
4. **Comprobante/PDF**: `GET /{id}/comprobante` genera el PDF a demanda desde los datos ya
   persistidos del movimiento (no se genera automáticamente al confirmar/registrar). `POST
   /{id}/pdf-firmado` guarda un PDF firmado manualmente (disco, vía `StorageRepositoryPort`).
   `GET /{id}/pdf-firmado` lo descarga — no hay URL estática (decisión de arquitectura ya
   tomada: backend solo-API).
5. **Entrada múltiple**: `POST /entradas/multiple` → por cada item, resuelve su ubicación
   (propia → global del request → `ALMACEN_GENERAL`), suma stock, recalcula `stock_actual` →
   crea un único `Movimiento` con todos los items embebidos. `require_authenticated` (igual
   que la entrada individual).
6. **Bitácora de ubicaciones**: al crear una ubicación o transferir stock entre dos (endpoints
   de `ubicaciones`, no de `movimientos`), el servicio correspondiente llama a
   `RegistradorDeMovimientosPort` **dentro de su propia transacción**, dejando un `Movimiento`
   tipo `creacion_ubicacion`/`transferencia_ubicacion`. Es un efecto secundario silencioso —
   no hay respuesta HTTP nueva, el registro solo aparece al listar/exportar movimientos.
7. **Salida múltiple directa**: `POST /salidas/multiple` → por cada item (con su propia
   ubicación obligatoria), valida stock, descuenta, recalcula `stock_actual` → crea un único
   `Movimiento` modalidad `multiple` con todos los items embebidos y remisión propia.
   `require_super_admin`.
8. **Salida por mercado**: `POST /salida-por-mercado` → resuelve el `MercadoPredefinido` por
   nombre (404 `MERC-002` si no existe) → multiplica cada `producto_kit.cantidad` por la
   cantidad de mercados solicitada → valida stock/descuenta en la **única ubicación explícita**
   indicada para todos los productos → crea un único `Movimiento` modalidad `mercado` con
   `nombre_mercado`/`referencia`. `require_super_admin`.
9. **Listar/exportar**: de solo lectura, sin `UnitOfWork`. Filtra por cualquiera de los 4
   valores de `tipo`, incluidos los de bitácora.

## Notas de comportamiento

- **`productos.stock_actual` nunca se actualiza con un `$inc` suelto** — siempre se recalcula
  como la suma de `ubicaciones.stock_fisico`, igual que el patrón ya establecido en el módulo
  `ubicaciones`. Corrige una inconsistencia real del legacy (`crear_movimiento` incrementaba
  `productos` y `ubicaciones` por separado, sin transacción).
- **La remisión es atómica** (`MongoGeneradorSecuencial`, `find_one_and_update` + `$inc`) —
  corrige una race condition real del legacy (`find_one` + `update_one` separados podían dar
  el mismo número a dos salidas concurrentes).
- El chequeo de stock insuficiente se hace **solo contra la ubicación**, no además contra el
  total denormalizado de `productos` (el legacy hacía ambos, de forma redundante una vez que
  `ubicaciones` es la fuente de verdad).
- El export a Excel **omite las columnas "Stock Anterior"/"Stock Actual"** del legacy — se
  calculaban desde un campo (`stock_actual` del propio movimiento) que el documento nunca
  guardó, así que siempre mostraban 0 en producción. Se prefirió omitirlas a reproducir un
  dato roto.
- **`ConfirmarReservaNormalService` descuenta stock una sola vez.** El legacy tenía un bug real:
  `crud.crear_movimiento` ya descontaba `stock_fisico`, y `confirmar_reserva` (router) volvía
  a descontar la misma ubicación con un `$inc` adicional — doble descuento en cada confirmación
  modo normal. No se reprodujo.
- **Detección de modalidad kit/múltiple** (para rechazarlas con `MOV-004`) usa la misma
  heurística del legacy: `datos_adicionales.tipo`, o `kitNombre` como señal de kit cuando no
  hay `tipo` explícito. Es una heurística sobre un dict libre, no un contrato tipado — se
  mantiene así porque `reservas.datos_adicionales` es intencionalmente `dict` libre (contexto
  para `movimientos`, ver `RESERVAS.md`).
- **`ReservaRepositoryPort.actualizar`/`eliminar` ahora aceptan `uow` opcional** (extensión del
  módulo `reservas`, retrocompatible) — necesario para que borrar la reserva participe de la
  misma transacción que el descuento de stock.
- `GeneradorSecuencialPort`/`ComprobantePort`/`StorageRepositoryPort` quedan module-scoped
  (`modules/movimientos/application/ports/`), no en `shared/` — mismo criterio que
  `EmailSenderPort` en `auth`: se promueven el día que aparezca un segundo consumidor real.
- **El ajuste de stock (descontar/incrementar) está centralizado en `AjustadorDeStockService`**
  (`application/services/ajustador_de_stock.py`), inyectado en `RegistrarSalidaService`,
  `RegistrarEntradaService`, `RegistrarSalidaMultipleService`, `RegistrarEntradaMultipleService`,
  `RegistrarSalidaPorMercadoService`, `ConfirmarReservaKitService`,
  `ConfirmarReservaMultipleService` y `ConfirmarReservaNormalService`. Antes cada uno
  reimplementaba la secuencia obtener producto/ubicación → validar → mutar `stock_fisico` →
  recalcular `stock_actual` (SOLID_MIGRATION_PLAN.md, Fase 1). Ninguno de estos 8 servicios
  recibe ya `ProductoRepositoryPort`/`UbicacionRepositoryPort` directamente en su constructor —
  solo `AjustadorDeStockService` los conoce.
- **`numero_cajas` siempre es `0` en modalidad kit.** El legacy lo trackeaba por item de
  reserva (`item.get('cajas')`), pero el `ItemReserva` de `reservas` no tiene ese campo, y
  ningún kit real en `inventario_db` lo tenía poblado — no se reabre `reservas` para un dato
  que nunca se usó en la práctica.
- **`ConfirmarReservaService` es un dispatcher** (patrón Strategy): lee la reserva una sola
  vez y delega a `ConfirmarReservaNormalService`/`ConfirmarReservaKitService`, que reciben la
  `Reserva` ya resuelta (no el `session_id`) y no repiten la detección de modalidad ni la
  lectura. Implementa la "interfaz común" que `MIGRATION_PLAN.md` sugería desde el análisis
  original del legacy.
- **Sin servir estáticos** (decisión de arquitectura ya tomada: backend solo-API): el PDF
  firmado subido se descarga vía `GET /{id}/pdf-firmado` (bytes en la respuesta), no una URL
  de archivo estático — mismo patrón que exportar Excel/generar comprobante.
- **`DiskStorageRepository` sanitiza el nombre de archivo subido** (`os.path.basename`,
  rechaza `..`/vacío) y verifica que la ruta resuelta quede dentro de `STORAGE_DIR` antes de
  leer o escribir — primera vez que el proyecto guarda archivos, sin este control un nombre de
  archivo adversarial (`../../etc/passwd`) podría escribir/leer fuera de la carpeta de
  almacenamiento.
- **La entrada múltiple registra la ubicación real usada, no un default falso.** El legacy
  resolvía el stock con `item.ubicacion or ubicacion_global or 'ALMACEN_GENERAL'` pero
  guardaba en el item persistido `item.ubicacion or 'ALMACEN_GENERAL'` — ignorando la
  ubicación global del request. Si un item no traía ubicación propia pero el request sí traía
  una global, el stock se aplicaba ahí, pero el documento mostraba `"ALMACEN_GENERAL"` (dato
  incorrecto). Corregido: el item persistido siempre refleja la ubicación real.
- **`tipo_origen` en entrada múltiple está restringido a un vocabulario fijo**
  (`compra`/`donacion`/`devolucion`/`traslado`/`ajuste`), a diferencia de la entrada
  individual donde es texto libre — mismo criterio que el legacy (solo
  `EntradaMultipleCreate` validaba esto). La validación vive tanto en el DTO de aplicación
  como en el schema HTTP, para que un valor inválido se resuelva como 422 en el borde de la
  API en vez de un 500 al construir el DTO interno.
- **La bitácora de `ubicaciones` (incremento 5) es puramente histórica** — `Movimiento.registrar_creacion_ubicacion`/`registrar_transferencia_ubicacion` no tocan stock; `ubicaciones` ya lo hizo antes de llamar al puerto, dentro de la misma transacción.
- **`RegistradorDeMovimientosPort` es propiedad de `ubicaciones`, no de `movimientos`** —
  patrón de inversión de dependencias explícito (ver Dependencias con otros módulos) para
  evitar el ciclo `movimientos↔ubicaciones`. El adaptador concreto sí vive en `movimientos`
  (es quien sabe construir un `Movimiento`) y resuelve `producto_nombre` por su cuenta, para
  que `ubicaciones` no tenga que conocerlo ni pasarlo.
- **3 bugs encontrados en la verificación end-to-end del incremento 5** (no durante el
  diseño): `ListarMovimientosInput`/`ExportarMovimientosExcelInput.tipo` estaban restringidos
  a `entrada`/`salida` (filtrar por un tipo de bitácora daba 500, no una lista vacía o
  resultados) — ampliados a los 4 valores de `TipoMovimiento`. El exportador de Excel
  etiquetaba cualquier tipo que no fuera `"entrada"` como `"SALIDA"` — una bitácora de
  ubicación se habría visto como salida de inventario en el reporte. `MovimientoResponse` no
  exponía `ubicacion_origen`/`ubicacion_destino` — los únicos campos que identifican una
  transferencia quedaban invisibles vía API. Los tres, corregidos.
- **3 desviaciones deliberadas del legacy en el incremento 6** (aprobadas explícitamente antes
  de construir, no asumidas): (1) `multiple`/`mercado` producen **un único** `Movimiento`
  embebido en vez de N movimientos separados — mismo patrón que `kit`. (2)
  `RegistrarSalidaPorMercadoService` exige **una ubicación explícita** para todos los productos
  del mercado — el legacy intentaba auto-elegir una ubicación llamando a
  `crud.get_ubicaciones_producto`, función que **no existe** en el código legacy real (bug
  nunca ejecutado en producción); no se reconstruyó ese heurístico. (3) El comprobante PDF de
  `multiple`/`mercado` se genera on-demand vía el endpoint ya existente, no automáticamente al
  registrar la salida — igual que `individual`/`kit`.
- **`ReportlabComprobanteAdapter` generalizado en el incremento 6**: el flag interno pasó de
  `es_kit` a `es_multi_producto` (`modalidad in {"kit", "multiple", "mercado"}`); agrega líneas
  `MERCADO PREDEFINIDO:`/`REFERENCIA:` cuando `nombre_mercado`/`referencia` están presentes; el
  título de la tabla de productos usa `kit_nombre` o `nombre_mercado` indistintamente.
- **`MovimientoSinProductosError` (`MOV-008`) es compartido** por `registrar_entrada_multiple`,
  `registrar_multiple` y `registrar_mercado` — su mensaje se generalizó (ya no menciona
  "entrada múltiple" específicamente) al agregarse los dos últimos casos de uso en el
  incremento 6.
- **Fuera de alcance, documentado como deuda futura**: "confirmar varias reservas en un
  comprobante" — el legacy nunca lo implementó, no hay comportamiento real que preservar. Se
  diseña de cero si en algún momento hay demanda real.

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `movimientos`": el plan completo de 6 incrementos
(priorizado por uso real, no por la intuición del plan original), la extensión de
`ReservaRepositoryPort` con `uow` (incremento 2), la decisión de inversión de dependencias para
la bitácora de `ubicaciones` (incremento 5 — evita el ciclo `movimientos↔ubicaciones`), y las
3 desviaciones deliberadas del legacy en múltiple/mercado (incremento 6, con sign-off explícito
antes de construir).

## Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

**Incremento 1**: usuario de prueba promovido a `super_admin` directamente en Mongo → crear
producto/ubicación de prueba → entrada individual (stock recalculado correctamente) → entrada
sin token (401) → salida individual (remisión `RM-001`, stock recalculado) → salida con stock
insuficiente (422, `MOV-003`) → salida a ubicación inexistente (404, `MOV-002`) → segunda
salida (`RM-002`, confirma la secuencia atómica) → listar con filtros combinados → listar sin
token (401) → exportar Excel (workbook válido, encabezados y filas correctas).

**Incremento 2**: producto/ubicación de prueba (stock 100) → armar reserva vía
`/api/reservas/{session_id}/ajustar` (+15) → confirmar sin token (401) → confirmar con rol
`operativo` (403) → confirmar sesión inexistente (404, `RES-002`) → confirmar una reserva
modalidad kit (400, `MOV-004`, sin tocar stock) → confirmar la reserva real (201, un
movimiento, remisión `RM-001`, `cliente_destino`/`motivo` correctos) → **stock descontado una
sola vez** (100 − 15 = 85, no 70) → reserva eliminada tras confirmar (404 al reconsultarla) →
confirmar de nuevo la misma sesión (404).

**Incremento 3**: dos productos/ubicaciones de prueba (stock 50 c/u) → armar reserva kit (5+2
unidades, `kitNombre`/`cliente`/`caso`) → confirmar (201, un solo movimiento modalidad kit,
`cantidad=1`, `numero_cajas=0`, 2 productos embebidos, `RM-001`) → stock descontado
correctamente en ambas ubicaciones → reserva eliminada → **regresión**: confirmar una reserva
normal después del refactor del dispatcher sigue funcionando (`RM-002`) → generar comprobante
del kit (200, PDF válido) → comprobante de movimiento inexistente (404, `MOV-005`) → subir PDF
firmado (200, `pdf_nombre` actualizado) → subir archivo no-PDF (400, `MOV-006`) → descargar el
PDF firmado (200, bytes idénticos) → descargar PDF de un movimiento sin PDF subido (404,
`MOV-007`).

**Incremento 4**: dos productos de prueba → entrada múltiple con un item con ubicación propia
y otro sin ubicación (usa la global del request) → 201, un solo movimiento modalidad
`entrada_multiple`, `cantidad=15`, `motivo="Compra"` → **el item sin ubicación propia registra
la ubicación global real**, no un `"ALMACEN_GENERAL"` falso (confirma la corrección del bug) →
stock recalculado correctamente en ambos productos → la ubicación global se creó de verdad con
el stock correcto → `tipo_origen` inválido (422) → `productos` vacío (422) → producto
inexistente (404, `PROD-002`) → sin token (401).

**Incremento 5**: producto de prueba → crear ubicación (stock 50) → **bitácora
`creacion_ubicacion`** con `producto_codigo`/`producto_nombre`/`ubicacion`/`cantidad`
correctos → exportar Excel filtrado por ese tipo con la etiqueta correcta (no `"SALIDA"`) →
crear segunda ubicación → transferir 15 unidades → **bitácora `transferencia_ubicacion`** con
`ubicacion_origen`/`ubicacion_destino` correctos y expuestos en la respuesta → stock real
verificado en ambas ubicaciones (35/15).

**Incremento 6**: dos productos con ubicaciones propias → `POST /salidas/multiple` con un item
por ubicación (403 con rol `operativo`) → un solo movimiento modalidad `multiple`, remisión
propia, stock descontado independientemente en cada ubicación, comprobante PDF descargable,
stock insuficiente (422) → mercado predefinido con 2 productos → ambos productos deben existir
en la **misma** ubicación explícita (comportamiento intencional) → `POST
/salida-por-mercado` (403 con rol `operativo`) → un solo movimiento modalidad `mercado` con
cantidades multiplicadas correctamente, `nombre_mercado`/`referencia` expuestos, comprobante
descargable, mercado inexistente (404, `MERC-002`) → reserva con
`datos_adicionales.tipo="multiple"` y 2 items → confirmar → un solo movimiento con motivo fijo,
stock descontado una sola vez, reserva eliminada tras confirmar.

`movimientos`/`contadores`/`reservas`/`ubicaciones`/`mercados_predefinidos` (legacy) verificados
intactos (58 documentos / `RM-023` / 3 reservas / 12 ubicaciones / 7 mercados — esta última es
la colección legacy `mercados_predefinidos`, separada de `catalogo_mercados_predefinidos`)
antes y después de los 6 incrementos. Datos de prueba y carpeta `storage/` de prueba eliminados
en cada caso. Suite completa: **280/280 tests verdes** (162 del resto del proyecto + 21 del
incremento 1 + 15 del incremento 2 + 30 netos del incremento 3 + 12 del incremento 4 + 15 del
incremento 5 + 25 del incremento 6).

## Nota post-cierre: `RegistrarSalidaPorMercadoService` revertido a ubicación por producto

La desviación deliberada (2) del incremento 6 — "una única ubicación explícita para todos los
productos del mercado" — resultó ser un problema real en uso, no solo teórico: un mercado
predefinido con productos que viven en ubicaciones físicas distintas (caso real detectado
probando el frontend) no podía venderse, porque cualquier ubicación indicada fallaba para
alguno de los productos (`MOV-002`).

Se revirtió a **una ubicación explícita por producto** (`RegistrarSalidaPorMercadoInput.productos:
list[ItemSalidaPorMercadoInput]`, cada uno con `producto_codigo`/`ubicacion`), igual patrón que
`RegistrarSalidaMultipleService` ya usaba. Nuevo error `MOV-009` (400) si falta la ubicación de
algún producto del kit. `docs/api/MOVIMIENTOS.md` actualizado con el contrato nuevo. No se
auto-selecciona ubicación (se mantiene la decisión original de no reconstruir el heurístico del
legacy) — el frontend ahora pide la ubicación real de cada producto del kit antes de habilitar
el envío.

## Nota post-cierre: registro directo de entrada revertido a exclusivo `super_admin`

Decisión de Fase 0 (ver arriba, "Permisos distintos para entrada/salida directa"): un
`operativo`/`admin` podía registrar una entrada directa e inmediata, sin aprobación —
asimétrico respecto a salida (siempre exclusiva `super_admin`).

El desarrollador pidió unificar el criterio: **ningún rol distinto de `super_admin` aplica un
movimiento directo** (ni entrada ni salida) — su única vía es proponerlo y esperar
confirmación, vía `aprobaciones_pendientes` (módulo separado, ya cubre exactamente este caso
para los 4 tipos: entrada/salida × individual/múltiple).

`RegistrarEntradaService`/`RegistrarEntradaMultipleService` (`POST /entradas` y
`POST /entradas/multiple`) pasaron de `require_authenticated` a `require_super_admin` —
mismo criterio que ya tenían `RegistrarSalidaService`/`RegistrarSalidaMultipleService`.
Verificado en vivo con un usuario `operativo` temporal (creado, probado, eliminado): antes
del cambio registraba una entrada directa con éxito; después, `403 AUTH-007` en ambos
endpoints, y `POST /aprobaciones-pendientes/entradas` le sigue funcionando sin cambios (201,
`estado: "pendiente"`) — el camino de propuesta no se tocó.

`docs/api/MOVIMIENTOS.md` actualizado (`require_authenticated` → `require_super_admin` en
ambos endpoints de entrada). Sin cambios en `aprobaciones_pendientes` — proponer una entrada
ya era, y sigue siendo, de cualquier rol autenticado.
