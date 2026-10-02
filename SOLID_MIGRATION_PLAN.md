# SOLID_MIGRATION_PLAN.md

> Guía oficial de implementación de principios SOLID sobre la arquitectura hexagonal ya
> vigente en este repositorio (`infrastructure → application → domain`, ver
> `.claude/ARCHITECTURE.md`).
>
> Este documento es un plan **vivo**: se actualiza a medida que se resuelven dudas o se
> completan fases. No contiene código. La ejecución avanza **fase por fase**, nunca de forma
> masiva, siguiendo la regla de oro de `.claude/WORKFLOW.md`: *no avanzar a la siguiente fase
> sin aprobar la anterior*.
>
> Ninguna fase de este plan reemplaza el flujo de `.claude/WORKFLOW.md`. Antes de escribir
> código en cualquier fase, se presenta el diseño concreto (nombres de clases/métodos, firmas,
> contratos) para aprobación — igual que la Fase 2 de un módulo nuevo.

---

## Decisiones de alcance ya acordadas

Estas decisiones fueron tomadas explícitamente con el desarrollador antes de detallar las
fases y aplican a **todo** el plan:

| Decisión | Resuelto | Detalle |
|---|---|---|
| Alcance de hallazgos a convertir en fases de cambio | **Solo severidad alta y media** | Los hallazgos de severidad baja (informativos o de mantenibilidad menor, no violaciones estrictas de SOLID) quedan documentados en la sección "Hallazgos revisados — sin cambio de código", con su justificación, pero **no** generan una fase de ejecución. |
| Registro de módulos (`shared/bootstrap/application.py`) y de colecciones Mongo (`shared/infrastructure/persistence/mongo/schema/registry.py`) | **Se mantiene el patrón manual explícito** | Ambos archivos violan OCP en sentido estricto (agregar un módulo/colección obliga a editar una lista existente). Se decidió **no** introducir auto-registro/descubrimiento porque cambiaría un patrón documentado explícitamente en `.claude/MONGODB.md`, `.claude/TEMPLATE.md` y `.claude/SOLID_CHECKLIST.md`, y el proyecto valora la trazabilidad explícita por encima de la extensibilidad automática en este punto. No se toca el mecanismo de registro en sí (ver Fase 5 para lo que sí cambia en `application.py`). |
| Segregación de puertos (ISP) | **Solo `ProductoRepositoryPort`** | Es el caso más claro: dos métodos que solo consume `inventario_reportes`, no `productos`. `UsuarioRepositoryPort` (auth, 10 métodos) se mantiene como está — es el patrón normal de Repository de agregado único y separar ahí tendría beneficio marginal. |
| Orden de ejecución de las fases | **Por impacto/severidad**, no por módulo | Primero el hallazgo de severidad alta (mayor riesgo real de bug), luego los de severidad media. No se sigue el orden de dependencias de `MIGRATION_PLAN.md`. |

Cualquier decisión nueva que surja durante el diseño de una fase específica se añade a la
tabla de esa fase como "Decisión pendiente" y se resuelve con el desarrollador antes de
escribir código de esa fase.

---

## Metodología de la auditoría

Se realizaron 3 auditorías de código paralelas, de solo lectura (sin modificar ningún
archivo), que en conjunto cubrieron el 100% de `modules/*/` (9 módulos) y `shared/`
(application, bootstrap, domain, infrastructure, utils), más `config/settings.py` y
`main.py`. Cada auditoría evaluó los 5 principios SOLID contra las reglas ya vigentes en
`.claude/ARCHITECTURE.md`, `.claude/CONVENTIONS.md` y `.claude/API.md`.

**Hallazgo de base confirmado:** no existe ningún import de `fastapi`, `motor`, `bson` ni
`pymongo` dentro de `domain/` o `application/` en ningún módulo. La regla de dependencias
`infrastructure → application → domain` se cumple estrictamente en todo el código actual.
Esto significa que el trabajo de este plan es de **refinamiento** sobre una base ya sólida,
no una corrección de arquitectura rota.

---

## Resumen de hallazgos

| # | Severidad | Principio | Ubicación | Acción |
|---|---|---|---|---|
| 1 | Alta | SRP + OCP | `modules/movimientos/application/services/*.py` (8 archivos) | **Fase 1 — ✅ Completada** |
| 2 | Media | LSP / contrato | `modules/movimientos/infrastructure/persistence/mongo/movimiento_repository.py:36-38` | **Fase 2 — ✅ Completada** |
| 3 | Media | OCP | `modules/aprobaciones_pendientes/application/services/confirmar_movimiento_pendiente.py:52-68` | **Fase 3** |
| 4 | Media | ISP | `modules/productos/application/ports/producto_repository.py:43-49` | **Fase 4** |
| 5 | Media | SRP | `shared/bootstrap/application.py:47-83` | **Fase 5** |
| 6 | Media (⚠️ alto radio de impacto) | DIP | `shared/infrastructure/api/dependencies/auth.py:6-18` | **Fase 6** — requiere confirmación explícita adicional antes de ejecutar |
| 7 | Alta (OCP estricto) | OCP | `shared/bootstrap/application.py:10-24,50-58` (registro de módulos) | Documentado, sin cambio (ver decisiones de alcance) |
| 8 | Alta (OCP estricto) / Media-Alta (DIP) | OCP + DIP | `shared/infrastructure/persistence/mongo/schema/registry.py:1-45` | Documentado, sin cambio (ver decisiones de alcance) |
| 9 | Baja-Media | ISP | `modules/auth/application/ports/usuario_repository.py:6-46` | Documentado, sin cambio |
| 10 | Media (defendible) | Acoplamiento entre módulos | `modules/inventario_reportes/application/dto/*.py` | Documentado, sin cambio |
| 11-17 | Baja | Varios | Ver "Hallazgos de baja severidad" | Fuera de alcance de este plan |

---

## Fases de implementación

### Fase 1 — [Severidad Alta] Unificar lógica de ajuste de stock duplicada en `movimientos` — ✅ Completada

**Diseño final aprobado:** se creó `AjustadorDeStockService` en
`modules/movimientos/application/services/ajustador_de_stock.py`, con dos métodos —
`descontar(producto_codigo, ubicacion, cantidad, creado_por, uow) -> Producto` e
`incrementar(producto_codigo, ubicacion, cantidad, creado_por, uow) -> Producto` — que hacen
siempre fetch + validar + mutar dentro de la `uow` recibida (se eligió simplificar, no
preservar la optimización de fail-fast que tenían `registrar_salida.py`/`registrar_entrada.py`
antes de abrir transacción). Los 8 servicios afectados ya no reciben
`ProductoRepositoryPort`/`UbicacionRepositoryPort` directamente en su constructor — solo
`AjustadorDeStockService` — lo que además redujo su superficie de dependencias. Wiring
actualizado en `modules/movimientos/infrastructure/api/dependencies.py`
(`get_ajustador_de_stock`). Tests: se agregó
`tests/unit/modules/movimientos/application/services/test_ajustador_de_stock.py` y se
actualizaron los 8 archivos de test existentes de los servicios afectados. Suite completa
(340 tests) pasando; `create_app()` verificado. Documentado en `.claude/modules/MOVIMIENTOS.md`.

**Por qué se cambia (SRP + OCP):**

La secuencia "obtener producto → validar existencia → obtener ubicación → validar
stock/existencia → mutar `stock_fisico` → recalcular `stock_actual` del producto sumando
todas sus ubicaciones → persistir" está duplicada casi literalmente en 8 servicios:

- `application/services/registrar_salida.py:74-92` (`_registrar`)
- `application/services/registrar_salida_multiple.py:82-120` (`_descontar_item`)
- `application/services/registrar_salida_por_mercado.py:110-149` (`_descontar_item`)
- `application/services/confirmar_reserva_kit.py:80-118` (`_descontar_item`)
- `application/services/confirmar_reserva_multiple.py:80-118` (`_descontar_item`, byte-idéntico al anterior)
- `application/services/confirmar_reserva_normal.py:71-121` (`_confirmar_item`)
- `application/services/registrar_entrada.py:53-72` (`_registrar`)
- `application/services/registrar_entrada_multiple.py:67-95` (`_registrar_item`)

Cada servicio de aplicación (cuya responsabilidad debería ser orquestar su caso de uso)
reimplementa una regla de negocio de bajo nivel (aritmética de stock por ubicación +
recálculo del total del producto) en vez de delegarla a un único componente. Cualquier
cambio en esa regla (nueva validación, corrección de un bug, un evento de dominio) obliga
hoy a tocar hasta 6 archivos en vez de uno. El propio código documenta que el legacy ya
tuvo bugs de este tipo (`registrar_salida_multiple.py:23-25`), lo que confirma que esta
duplicación no es solo teórica.

**Qué se propone cambiar (a discutir en el diseño de la fase, aún no aprobado):**

Extraer un componente compartido dentro de `modules/movimientos/application/` (nombre y
forma exactos a definir en la Fase 2 de esta sub-tarea, siguiendo `.claude/WORKFLOW.md`)
con responsabilidad única: dado un producto/ubicación/cantidad, validar y aplicar el
ajuste de stock (incremento o descuento) y devolver el resultado, usando los puertos ya
existentes (`ProductoRepositoryPort`, `UbicacionRepositoryPort`, `UnitOfWorkPort`). Los 8
servicios pasarían a inyectarlo por constructor y delegar en él, en lugar de reimplementar
la lógica.

**Archivos afectados (estimado, se confirma en diseño):**
- Nuevo archivo en `modules/movimientos/application/services/` (o `domain/` si la lógica
  resulta ser pura de dominio sin I/O — a decidir en el diseño).
- Los 8 servicios listados arriba (constructor + llamada).
- `modules/movimientos/infrastructure/api/dependencies.py` (cablear el nuevo componente).
- Tests unitarios nuevos para el componente extraído.
- Tests existentes de los 8 servicios: ajustar mocks/fixtures al nuevo constructor.

**Tests:** obligatorio por `.claude/TESTING.md`. Se agregan pruebas unitarias del
componente nuevo (casos: stock suficiente, stock insuficiente, ubicación inexistente,
producto inexistente) y se verifica que los 8 tests de servicios existentes sigan
pasando tras el cambio de constructor.

**Docs:** actualizar `.claude/modules/MOVIMIENTOS.md` si el cambio es significativo
(lo es — cambia la composición interna de 8 servicios).

**Cierre de fase:** recorrer `.claude/SOLID_CHECKLIST.md` completo antes de considerar
la fase cerrada.

---

### Fase 2 — [Severidad Media] Validar `ObjectId` antes de convertir en `MongoMovimientoRepository.obtener_por_id` — ✅ Completada

**Resultado:** se agregó el guard `if not ObjectId.is_valid(movimiento_id): return None` al
inicio de `obtener_por_id`, igual al patrón ya usado en `MongoUsuarioRepository` de `auth`. Se
confirmó por grep que `movimiento_id` llega sin validar desde 3 rutas HTTP
(`GET /movimientos/{id}/comprobante`, `GET/POST .../pdf-firmado`) hasta 3 servicios
(`GenerarComprobantePdfService`, `ObtenerPdfFirmadoService`, `SubirPdfFirmadoService`), y que
los 3 ya manejan correctamente un `None` de retorno lanzando `MovimientoNoEncontradoError` (404)
— no fue necesario tocar esos servicios. `actualizar()` no requirió el mismo guard: su
`movimiento.id` proviene siempre de una entidad ya obtenida (id ya validado), nunca de un path
param HTTP crudo. Test nuevo agregado a
`tests/unit/modules/movimientos/infrastructure/persistence/mongo/test_movimiento_repository.py`.
Suite completa (341 tests) pasando.

**Por qué se cambia (LSP / fidelidad de contrato):**

`modules/movimientos/infrastructure/persistence/mongo/movimiento_repository.py:36-38`:

```python
async def obtener_por_id(self, movimiento_id: str) -> Movimiento | None:
    doc = await self._col.find_one({"_id": ObjectId(movimiento_id)})
```

El puerto (`application/ports/movimiento_repository.py:16-18`) documenta que el método
devuelve `None` si no existe — no documenta que pueda lanzar. Si `movimiento_id` no es un
`ObjectId` válido (p. ej. llega como path param HTTP arbitrario en
`GET /movimientos/{id}/comprobante` o `/pdf-firmado`), `ObjectId(movimiento_id)` lanza
`bson.errors.InvalidId`, no capturado en los servicios que lo llaman
(`GenerarComprobantePdfService`, `ObtenerPdfFirmadoService`, `SubirPdfFirmadoService`) →
el cliente recibe un 500 en vez de un 404/422. El mismo tipo de repositorio en `auth`
(`modules/auth/infrastructure/persistence/mongo/usuario_repository.py:21-25,82-86`) sí
valida con `ObjectId.is_valid(...)` antes — es una inconsistencia de cumplimiento de
contrato entre implementaciones hermanas del mismo patrón.

**Qué cambia:** agregar el guard `if not ObjectId.is_valid(movimiento_id): return None`
al inicio de `obtener_por_id` (y revisar si `actualizar` u otros métodos del mismo
repositorio necesitan el mismo guard, a confirmar en diseño).

**Tests:** agregar caso `test_obtener_por_id_con_id_invalido_retorna_none` en
`tests/unit/modules/movimientos/infrastructure/...` (o donde corresponda según
`.claude/TESTING.md` — a confirmar si el proyecto testea repositorios Mongo con mocks o
solo vía integración; si solo se testea a nivel de servicio/HTTP, la prueba se ubica ahí).

**Docs:** no requiere cambio en `.claude/modules/MOVIMIENTOS.md` (es un detalle interno
de infraestructura, no cambia contrato público).

---

### Fase 3 — [Severidad Media] Reemplazar cadena `if/elif` por tabla de mapeo en `ConfirmarMovimientoPendienteService`

**Por qué se cambia (OCP):**

`modules/aprobaciones_pendientes/application/services/confirmar_movimiento_pendiente.py:52-68`
tiene una cadena `if/elif/elif/else` sobre `pendiente.tipo_propuesto`
(`"entrada"`, `"entrada_multiple"`, `"salida"`, `"salida_multiple"`) para decidir qué
`Input` DTO reconstruir desde `payload` y qué método de `EjecutorDeMovimientosPort`
invocar. Agregar un nuevo tipo propuesto obliga a modificar este método, además del
`Literal` en `domain/entities/movimiento_pendiente.py:10` y el `$jsonSchema` de
`movimientos_pendientes_collection.py:21` (estos dos últimos son inherentes al dominio y
no se eliminan con este cambio, solo el despacho en el servicio).

**Qué cambia:** reemplazar la cadena `if/elif` por una tabla de mapeo
`tipo_propuesto -> (constructor de Input, método ejecutor)`, de forma que agregar un tipo
sea agregar una entrada a la tabla en vez de tocar el cuerpo del método. Forma exacta a
proponer en el diseño de la fase.

**Tests:** los tests existentes de `ConfirmarMovimientoPendienteService` deben seguir
pasando sin cambios de comportamiento observable; se agrega un test que confirme que un
`tipo_propuesto` no soportado sigue lanzando el error de dominio esperado.

**Docs:** no requiere cambio en `docs/api/APROBACIONES_PENDIENTES.md` (no cambia
contrato HTTP). Revisar si `.claude/modules/APROBACIONES_PENDIENTES.md` describe este
flujo internamente y necesita actualización menor.

---

### Fase 4 — [Severidad Media] Segregar `ProductoRepositoryPort` (ISP)

**Por qué se cambia (ISP):**

`modules/productos/application/ports/producto_repository.py:7-49` define 9 métodos.
Ningún servicio de `productos` usa `listar_bajo_stock()` (líneas 43-45) ni
`calcular_valor_total()` (líneas 47-49) — esos dos métodos los consume exclusivamente
`inventario_reportes` (`obtener_valor_total_inventario.py:9`,
`obtener_reporte_inventario.py:20-21`, `obtener_estadisticas_dashboard.py:22`,
`listar_productos_bajo_stock.py:10`). El puerto propio de `productos` mezcla su contrato
CRUD con dos consultas de reporting que existen solo para servir a un consumidor externo.
No rompe nada hoy (un solo repositorio Mongo implementa todo), pero es el patrón exacto
que complica el día que haya un segundo adaptador (caché, repositorio in-memory de test)
que tendría que implementar métodos de reporting irrelevantes para él.

**Qué cambia:** extraer `listar_bajo_stock` y `calcular_valor_total` a un puerto nuevo
(nombre a definir en diseño, p. ej. `ProductoConsultaReportePort`), implementado por el
mismo `MongoProductoRepository` (o una clase separada, a decidir), consumido únicamente
por los servicios de `inventario_reportes`. `ProductoRepositoryPort` queda con el
contrato CRUD puro que sí usan todos los servicios de `productos`.

**Archivos afectados (estimado):**
- `modules/productos/application/ports/producto_repository.py` (quitar 2 métodos).
- Nuevo puerto (ubicación a definir: ¿vive en `productos/application/ports/` porque lo
  implementa el repositorio de `productos`, o en `inventario_reportes/application/ports/`
  porque es quien lo consume? — **pregunta para el diseño de la fase**, ya que
  `.claude/ARCHITECTURE.md` no cubre este caso de puerto cruzado entre dos módulos de
  forma explícita; el patrón más cercano ya usado en el repo es
  `RegistradorDeMovimientosPort`, donde el puerto lo define quien lo **necesita**
  (`ubicaciones`) y lo implementa quien lo **provee** (`movimientos`) — se propondrá
  seguir ese mismo patrón, a confirmar).
- `modules/productos/infrastructure/persistence/mongo/producto_repository.py` (implementa
  ambos puertos).
- `modules/productos/infrastructure/api/dependencies.py` y
  `modules/inventario_reportes/infrastructure/api/dependencies.py` (recablear inyección).
- Los 4 servicios de `inventario_reportes` que usan estos métodos (cambiar el tipo del
  puerto inyectado).

**Tests:** actualizar mocks en tests de los 4 servicios de `inventario_reportes` para que
inyecten el nuevo puerto en vez de `ProductoRepositoryPort` completo. No debería requerir
tests nuevos de lógica (el comportamiento no cambia, solo el contrato del tipo).

**Docs:** actualizar `.claude/modules/PRODUCTOS.md` e
`.claude/modules/INVENTARIO_REPORTES.md` si documentan los puertos disponibles.

---

### Fase 5 — [Severidad Media] Descomponer `create_app()` en `shared/bootstrap/application.py` (SRP)

**Por qué se cambia (SRP):**

`create_app()` (`shared/bootstrap/application.py:47-83`) combina: construcción del
`FastAPI`, registro de error handlers, registro de 9 módulos de negocio, configuración de
middlewares (Security headers + CORS), y definición inline de dos endpoints ad-hoc (`/` y
`/redoc` personalizado). Son al menos 4 responsabilidades distintas en una función de 36
líneas.

**Importante — qué NO cambia:** por la decisión de alcance ya acordada, el **registro
manual y explícito de cada módulo** (import + llamada a `register_module_xxx(app)`) se
mantiene tal cual, línea por línea — esta fase no introduce auto-descubrimiento ni cambia
el flujo documentado en `.claude/TEMPLATE.md`/`.claude/MONGODB.md`. Solo se reorganiza el
código en funciones privadas con una responsabilidad cada una.

**Qué cambia:** extraer funciones privadas dentro del mismo archivo, por ejemplo
`_registrar_modulos(app)`, `_configurar_middlewares(app)`, `_registrar_rutas_base(app)`
(nombres exactos a confirmar en diseño), dejando `create_app()` como orquestador delgado
que las llama en orden. El cuerpo de `_registrar_modulos` sigue siendo la misma lista
explícita de llamadas que hoy.

**Tests:** este archivo no tiene tests unitarios hoy (es composition root, se prueba
indirectamente por los tests de integración/arranque si existen). Se revisa si
`tests/integration/` tiene algo que dependa de la estructura interna de `create_app()`
antes de tocarlo.

**Docs:** no requiere cambios en `.claude/*.md` — el comportamiento externo no cambia.

---

### Fase 6 — [Severidad Media, ⚠️ alto radio de impacto] `shared/infrastructure/api/dependencies/auth.py` depende de infraestructura concreta de `auth`

**Por qué se marca (DIP):**

`shared/infrastructure/api/dependencies/auth.py:6-18` importa, además de puertos (ABCs,
correcto), tipos y funciones concretas de `modules.auth.infrastructure.api.dependencies`
(`get_token_port`, `get_usuario_repository`). El propio archivo documenta esto como una
decisión ya tomada explícitamente con el desarrollador en `MIGRATION_PLAN.md:117` (Fase 0
del módulo `auth`): la dependencia HTTP "usuario actual" vive en `shared/` "consumiendo un
puerto expuesto por auth". El hallazgo real es que hoy consume, además del puerto, la capa
de infraestructura concreta de `auth` (sus funciones `get_*` de `Depends`), no solo el
puerto en sí.

**Por qué esta fase se marca distinto a las demás:** `get_current_usuario`/`require_roles`
son consumidos por **todas** las rutas protegidas de **todos** los módulos del sistema. Un
cambio aquí, aunque sea correcto en diseño, tiene el radio de impacto más grande de todo
este plan. **No se ejecuta esta fase sin una confirmación explícita adicional del
desarrollador en el momento de abordarla**, incluso aunque este plan general ya esté
aprobado — se re-preguntará específicamente antes de tocar este archivo.

**Qué se propondría cambiar (a validar, no decidido):** definir un puerto de
autenticación genérico en `shared/application/ports/` (p. ej. algo que exponga
"resolver usuario actual desde un token" sin conocer los tipos concretos de DI de
`auth/infrastructure`), implementado/cableado por `auth`. Alternativa más conservadora:
dejar el import de `UsuarioRepositoryPort`/`TokenPort` (son puertos, ya cumplen DIP) pero
eliminar el import de las funciones `get_*` de `modules.auth.infrastructure.api.dependencies`,
resolviendo esas dependencias de otra forma. Ambas opciones se presentan en el diseño de
la fase para que el desarrollador elija.

**Tests:** `shared/infrastructure/api/dependencies/auth.py` es consumido transitivamente
por los tests de cada módulo que protege rutas — se requiere correr la suite completa
antes de cerrar esta fase, no solo los tests nuevos.

**Docs:** revisar si `docs/api/AUTH.md` o `.claude/modules/AUTH.md` describen este
mecanismo y necesitan actualización.

---

## Hallazgos revisados — sin cambio de código

Documentados por transparencia, con su justificación. No generan fase de ejecución.

| Hallazgo | Ubicación | Justificación de no-acción |
|---|---|---|
| OCP: registro manual de 9 módulos | `shared/bootstrap/application.py:10-24,50-58` | Decisión de alcance ya acordada: se prefiere la explicitud y trazabilidad del registro manual sobre la extensibilidad automática. Cambiar esto implicaría además actualizar `.claude/TEMPLATE.md` y `.claude/MONGODB.md`, que documentan el flujo manual como el estándar del proyecto. |
| OCP + DIP: `registry.py` importa 8 módulos de negocio desde `shared/` | `shared/infrastructure/persistence/mongo/schema/registry.py:1-45` | Misma decisión que el punto anterior — es el mismo patrón aplicado a colecciones Mongo, documentado explícitamente en `.claude/MONGODB.md:32` como el flujo estándar de alta de colección. |
| ISP: `UsuarioRepositoryPort` (10 métodos) | `modules/auth/application/ports/usuario_repository.py:6-46` | Es el patrón normal de Repository de agregado único (todo gira en torno a `Usuario`). Ningún servicio necesita implementar el puerto completo (solo lo consume tipado), y no hay hoy un segundo adaptador que sufra el costo de una interfaz ancha. Beneficio marginal frente al costo de fragmentar el puerto. |
| Acoplamiento: DTOs de `inventario_reportes` reexportan entidades de `productos`/`movimientos` | `modules/inventario_reportes/application/dto/*.py` | `inventario_reportes` es explícitamente un módulo de solo lectura/agregación sobre otros dominios; reusar sus entidades en vez de duplicar su forma en DTOs propios es una decisión de diseño defendible para este tipo de módulo, no una fuga de responsabilidad. |

### Hallazgos de baja severidad (fuera de alcance de este plan)

| # | Hallazgo | Ubicación |
|---|---|---|
| 11 | Mapeo duplicado de `Movimiento` entre `aprobaciones_pendientes` y `movimientos` | `modules/aprobaciones_pendientes/infrastructure/api/routes.py:100-130` |
| 12 | Cadena `if` (3 casos) en vez de tabla de despacho para modalidad de reserva | `modules/movimientos/application/services/confirmar_reserva.py:49-58` |
| 13 | Resolución de `creado_por.id_persona` (decisión de negocio) ejecutada en el repositorio de infraestructura en vez de en dominio | `modules/auth/infrastructure/persistence/mongo/usuario_repository.py:41-58` |
| 14 | Método privado `_resolver_productos` duplicado idéntico entre dos servicios | `modules/mercados_predefinidos/application/services/{crear,actualizar}_mercado_predefinido.py` |
| 15 | Estado mutable a nivel de clase / lectura de `settings` en tiempo de import | `shared/infrastructure/persistence/mongo/database.py:11-12` |
| 16 | Utilidad "genérica" con acoplamiento semántico a un proveedor de IA específico | `shared/utils/archivos.py:3` |
| 17 | Lógica de reintento mezclada con acceso al secreto en un mismo método | `shared/infrastructure/gcp/secret_manager.py:19-61` |

Si en el futuro se decide abordar alguno de estos, se agrega como fase nueva a este mismo
documento (no se ejecuta sin pasar primero por la aprobación de diseño correspondiente).

---

## Patrones que ya cumplen SOLID correctamente (no se tocan)

Para que quede explícito qué **no** se va a modificar porque ya es un buen ejemplo del
principio correspondiente:

- Inyección de dependencias por constructor en absolutamente todos los application
  services auditados (DIP) — la resolución concreta ocurre solo en
  `infrastructure/api/dependencies.py` de cada módulo.
- `RegistradorDeMovimientosPort` (`ubicaciones` define, `movimientos` implementa) y
  `EjecutorDeMovimientosPort` (`movimientos` define, `aprobaciones_pendientes` consume) —
  ejemplo correcto de puerto cruzado entre módulos para romper ciclos de dependencia sin
  imports directos entre capas `application` (DIP + ISP).
- `modules/ejemplo_tareas/` completo — módulo de referencia del template, usado como
  patrón a replicar; no requiere cambios.
- Entidades de dominio con factories/mutadores inmutables que encapsulan invariantes
  (`Usuario.crear`, `Movimiento.registrar_salida`, `MercadoPredefinido.actualizar`, etc.).
- Pipelines Mongo extraídos a `infrastructure/persistence/mongo/pipelines/*.py` como
  builders que extienden `ConstructorPipelineBase` (OCP correcto vía herencia/composición).
- `movimientos_excel_exporter.py:7-12` usa tabla de mapeo (`_ETIQUETA_TIPO`) en vez de
  `if/elif` — ejemplo correcto de OCP ya aplicado en el propio código.
- `shared/application/persistence/unit_of_work.py` (`UnitOfWorkPort`) — puerto mínimo de 3
  miembros, implementación (`MongoUnitOfWork`) fiel al contrato.
- Rutas FastAPI (`infrastructure/api/routes.py`) en todos los módulos auditados: traducción
  HTTP pura, sin lógica de negocio embebida.

---

## Reglas transversales aplicables a TODAS las fases

Recordatorio explícito — ninguna fase de este plan puede violar lo ya establecido en
`.claude/`:

- No crear `__init__.py` en ningún directorio nuevo (namespace packages).
- `domain/` y `application/` siguen sin importar FastAPI, Motor, Pydantic (salvo DTOs,
  donde ya está permitido) ni SDKs cloud.
- Todo cambio de lógica incluye o actualiza sus pruebas unitarias en
  `tests/unit/modules/<modulo>/...` o `tests/unit/shared/...`, espejando la estructura de
  `.claude/TESTING.md`. Sin excepción documentada explícita.
- Ninguna fase avanza sin la aprobación explícita del desarrollador sobre el diseño
  concreto propuesto (regla de oro de `.claude/WORKFLOW.md`).
- Si el cambio de una fase es significativo para un módulo, se actualiza
  `.claude/modules/<MODULO>.md` correspondiente.
- Al cerrar cada fase, se recorre `.claude/SOLID_CHECKLIST.md` completo antes de darla por
  terminada.
- Ninguna fase de este plan se ejecuta de forma masiva: archivo por archivo, con revisión
  intermedia.

---

## Próximos pasos

Este documento queda pendiente de revisión del desarrollador. Al aprobarlo, se inicia la
**Fase 1** siguiendo el mismo patrón de `.claude/WORKFLOW.md`: primero se presenta el
diseño concreto del componente a extraer (nombre, métodos, firmas, ubicación exacta) para
aprobación — todavía sin código — y solo después de ese visto bueno se construye,
con sus pruebas unitarias correspondientes.
