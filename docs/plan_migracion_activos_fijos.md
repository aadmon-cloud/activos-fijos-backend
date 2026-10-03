# Plan de Migración — Sistema de Gestión de Activos Fijos, Elementos e Inventario

## 0. Objetivo y alcance de este documento

Este documento consolida:

1. El análisis completo del backend legacy (`BACKEND VIEJO/`): qué existe realmente, qué está roto, qué está vacío y qué datos ya cargados deben preservarse.
2. El mapeo de esa lógica hacia los módulos del nuevo sistema, incluyendo el cambio conceptual **tickets → solicitudes**.
3. Los hallazgos de seguridad (OWASP Top 10) detectados en el legacy y cómo se neutralizan con la arquitectura del proyecto nuevo.
4. El **modo de trabajo** para construir cada módulo nuevo aplicando arquitectura hexagonal, SOLID y las convenciones ya definidas en `.claude/`.

Este documento **no reemplaza** `.claude/WORKFLOW.md`, `.claude/ARCHITECTURE.md`, `.claude/SOLID_CHECKLIST.md` ni `docs/arquitectura_hexagonal.md` — es el plan maestro que se sitúa **antes** de esos flujos: define *qué* módulos construir y *en qué orden*, dejando que cada módulo individual siga el proceso de 4 fases ya establecido en `WORKFLOW.md`.

**Regla de oro heredada de `WORKFLOW.md` y que aplica también a este plan:** no se avanza a construir un módulo sin que su alcance (Fase 0) y su modelado Mongo (Fase 1) hayan sido acordados explícitamente.

---

## 1. Resumen ejecutivo del análisis del backend legacy

El legacy (`BACKEND VIEJO/app`) es una API FastAPI + MongoDB **sin arquitectura hexagonal**: toda la lógica vive en los endpoints, sin capas `domain`/`application`, con acceso a Mongo vía `Depends(get_database)` (el anti-patrón exacto que el proyecto nuevo prohíbe).

Hallazgo más importante para planificar el trabajo: **buena parte de la lógica de negocio descrita en el encargo no existe realmente en el código**, aunque los nombres de archivo sugieran que sí:

| Módulo legacy | Estado real |
|---|---|
| `activos` | **Funcional.** CRUD completo con reglas de negocio, aunque con bugs (ver §5). |
| `areas`, `categorias`, `estados` | **Funcional** para creación/listado. Borrado roto (bug de tipos). |
| `usuarios` / `auth` | **Funcional** (registro, login, JWT), con una vulnerabilidad crítica de escalación de privilegios (ver §5). |
| `tickets` | **Parcialmente funcional.** Máquina de estados lineal simple, sin aprobaciones, sin enrutamiento por área. |
| `dashboard` | **No existe.** Archivo vacío, no registrado. |
| `mantenimientos` | **No existe funcionalmente.** Sin modelo, sin schema, sin endpoints (archivo vacío). Solo se *lee* la colección desde `activos.py`, nunca se escribe. |
| `movimientos` | **No existe funcionalmente.** Igual que mantenimientos: solo lectura, cero escritura en todo el código. |
| `notificaciones` (como entidad/colección) | **No existe.** Ni modelo, ni schema, ni endpoint, ni una sola referencia a una colección `notificaciones`. |
| `workflow_service.py` (el supuesto orquestador de aprobaciones) | **Vacío (0 bytes).** No hay motor de aprobación ni enrutamiento automático en ningún lugar del código. |
| Envío de correos (`email_service.py`) | **Roto en producción.** El método que arma el correo de creación de ticket nunca llama a `_send_email(...)`; dos métodos adicionales están definidos fuera de la clase (no son invocables) y no se usan desde ningún otro archivo. |
| `tipo_activo` | Tiene código pero **no está montado** en el router; además importa un módulo inexistente. |

**Conclusión operativa:** para *Activos*, *Áreas*, *Categorías*, *Estados* y *Usuarios* hay lógica de negocio real que analizar y adaptar. Para *Solicitudes* (ex-tickets) hay una base parcial (tipos, estados, seguimiento) pero el enrutamiento y las aprobaciones descritas en el encargo **deben diseñarse desde cero**. Para *Mantenimientos*, *Movimientos*, *Notificaciones* y *Dashboard* **no hay lógica legacy que migrar** — son diseño nuevo casi en su totalidad; lo único reutilizable son nombres de campos y la intención funcional.

---

## 2. Inventario detallado por entidad (legacy)

### 2.1 Activo

Colección `activos`. Campos reales: `nombre`, `numero_inventario` (único), `marca`, `modelo`, `serie`, `descripcion`, `categoria_id` (ObjectId → `categorias`), `riesgo_biomedico`, `categoria_biomedica`, `estado` (**referencia por nombre de texto**, no por ID, a `estados`), `responsable_id` (ObjectId → `usuarios`), `area_id` (ObjectId → `areas`), `ubicacion` (embebido: edificio/piso/oficina/estantería/posición), `complementos` (lista embebida: nombre/descripción/cantidad/serie), `observaciones`, `foto_url`, `ficha_tecnica_url`, `historial` (array embebido de cambios), `created_at`/`updated_at`.

Se ajusta casi por completo al modelo pedido en el encargo (nombre, placa, categoría, estado, responsable, área, fecha adquisición, valor, observaciones, foto, ficha técnica). **Falta**: campo `valor` (no existe en el legacy pese a estar en el encargo), y `fecha_adquisicion` explícita (solo hay `created_at`, que no es lo mismo).

### 2.2 Área / Categoría / Estado (catálogos)

Estructura mínima y equivalente entre las tres: `nombre`, `descripcion`, `created_at` (Estado añade `color`). Son catálogos de referencia simples, sin jerarquía ni estado activo/inactivo.

**Dato clave: ya existen datos cargados en producción** (sembrados por `scripts/init_db.py`):

- **17 áreas**: Dirección, Jurídico, Administración, Talento Humano, Familias Productivas, Gestión, Ayúdanos a Ayudar, Jornadas de Apoyo, Ayúdanos a Educar, Comunicaciones, Contabilidad, Campus, Tecnología, Recepción, Cooperación Internacional, Compras, Tesorería.
- **7 categorías**: Muebles, Equipos de Cómputo, Equipos Eléctricos, Equipos Biomédicos, Equipo de Comunicaciones, Elementos Logística, Equipo de Sonido e Iluminación.
- **3 estados**: Bueno (`#4CAF50`), Excelente (`#2196F3`), Regular (`#FFC107`). El encargo pide además: Disponible, Prestado, En mantenimiento, Dado de baja, Perdido, Dañado — **son conceptos distintos** (calidad física vs. disponibilidad/ciclo de vida), ver §3 para la decisión de modelado.
- **2 usuarios administradores** ya operativos (correos reales `@fundacionmarialuisa.org`, roles `super_admin`/`admin`, área Dirección).

### 2.3 Usuario

`email`, `nombre`, `apellido`, `password` (hash bcrypt), `rol` (string libre, sin enum — origen de la vulnerabilidad crítica de §5), `area_id` (**guardado como string**, inconsistente con el resto de referencias que usan `ObjectId`), `telefono`, `identificacion` (único), `activo` (bool), `created_at`/`updated_at`.

Roles legacy: `empleado`, `admin`, `super_admin` (solo 3, sin roles funcionales como Tecnología/Mantenimiento). El encargo pide 6 roles funcionales (Administrador General, Tecnología, Mantenimiento, Administrativo, Jefe de Área, Empleado) — ver mapeo en §6.6.

### 2.4 Ticket (→ Solicitud)

Sin modelo/schema formal (inferido del código): `tipo` (`SOPORTE_TECNICO`, `MANTENIMIENTO`, `CAMBIO`, `PAPELERIA`), `titulo`, `descripcion`, `prioridad` (string libre, sin enum real), `estado` (`NUEVO → VISTO → EN_PROCESO → RESUELTO → CERRADO`, transición libre sin matriz), `solicitante_id` (ObjectId), `responsables` (**lista de emails**, no ObjectIds), `activos_ids` (sin castear a ObjectId — no cruza correctamente con `activos`), `seguimiento` (array embebido de comentarios/cambios de estado), timestamps por hito.

No existe: enrutamiento automático a un área, concepto de "aprobador" distinto de "responsable", ni rechazo. El campo `responsables` se llena a mano por quien crea el ticket.

### 2.5 Mantenimiento / Movimiento / Notificación

Sin modelo, schema ni endpoint activo. Los únicos rastros son lecturas puntuales en `activos.py` (para armar un "historial completo" agregando tickets + mantenimientos + movimientos + historial embebido). **Ninguna parte del código legacy escribe en estas colecciones.** Se tratan como diseño 100% nuevo.

### 2.6 Historial

No es colección propia: es un array embebido dentro de cada `activo`, generado automáticamente comparando campo por campo en cada `update()`. Este patrón **entra en conflicto** con lo que exige `.claude/MONGODB_MODELING.md` para el nuevo proyecto (ver §7.3).

---

## 3. Hallazgos de seguridad — OWASP Top 10 en el legacy

| # OWASP | Hallazgo concreto en legacy | Mitigación obligatoria en el nuevo sistema |
|---|---|---|
| **A01 — Broken Access Control** | `POST /auth/register` es público y persiste el `rol` tal cual lo envía el cliente → cualquiera puede autoregistrarse como `super_admin`. | El endpoint de registro de usuarios **no será público**: solo un rol administrativo puede crear usuarios y asignar rol. `rol` modelado como `Enum` cerrado en el dominio, nunca como string libre aceptado del cliente sin whitelist. |
| **A01 — Broken Access Control** | Chequeos de rol duplicados y **inconsistentes** copy-paste en cada endpoint (`tipos_activo.py` excluye a `super_admin` por error). `core/dependencies.py` (el lugar obvio para centralizar) está vacío. | Autorización centralizada como dependencia reutilizable en `shared/infrastructure/api/dependencies/` (p. ej. `requiere_rol(*roles)`), nunca repetida a mano por módulo. |
| **A01 — Broken Access Control** | `DELETE` de áreas/categorías/estados no valida integridad referencial de forma efectiva (bug de tipos ObjectId/string hace que el chequeo "no borrar si tiene activos asociados" nunca se dispare). | Las reglas de integridad referencial son responsabilidad del **dominio/aplicación** (servicio de borrado), con tests unitarios que cubran explícitamente el caso "no se puede borrar si está en uso". |
| **A02 — Cryptographic Failures** | `SECRET_KEY` de JWT tiene un valor por defecto hardcodeado si no se configura `.env`. | Sin valores por defecto inseguros: `pydantic-settings` sin default para secretos — el servicio debe fallar al arrancar si falta, tal como ya hace `config/settings.py` en la plantilla nueva. |
| **A03 — Injection** | Validaciones ad-hoc con regex propias reimplementando lo que Pydantic ya resuelve (`validate_email`); varios endpoints reciben `dict` genérico sin schema (`tickets.py`). | Todo input HTTP tipado con `Pydantic` en `infrastructure/api/schemas.py`, sin excepciones "por ahora uso un dict". |
| **A04 — Insecure Design** | No existe motor de aprobación/enrutamiento (`workflow_service.py` vacío) pese a que el negocio lo requiere — el diseño de "Movimiento 2" (préstamo entre áreas) exige 5 pasos secuenciales de aprobación que en el legacy simplemente no existen. | Diseñar explícitamente máquinas de estado con transiciones válidas (no libres) para `solicitudes` y `movimientos`, como parte de la Fase 2 (diseño de dominio) de cada módulo. |
| **A05 — Security Misconfiguration** | CORS abierto (`allow_origins=["*"]`, `allow_credentials=True` simultáneamente — combinación insegura) ya presente incluso en la plantilla nueva (`shared/bootstrap/application.py`). | Revisar configuración de CORS antes de ir a producción: orígenes explícitos por entorno, no wildcard combinado con credenciales. |
| **A07 — Identification and Authentication Failures** | Sin rate limiting en login, sin bloqueo tras intentos fallidos, sin expiración/rotación de tokens, sin recuperación de contraseña. | Diseñar el módulo `usuarios`/autenticación end-user con estas protecciones desde el día uno (documentar explícitamente qué queda fuera del alcance inicial si se decide diferir). |
| **A08 — Software and Data Integrity Failures** | Falla silenciosa de envío de correo sin logging (`email_service.py`) — nadie se entera en producción de que las notificaciones no llegan. | Los adaptadores de infraestructura (envío de correo, storage de archivos) deben propagar error como `DomainError` de categoría `integration` (502), nunca fallar en silencio. |
| **A09 — Security Logging and Monitoring Failures** | `except:` desnudos que capturan cualquier excepción y la convierten en 404, ocultando errores reales de programación; sin logging estructurado. | Usar `configurar_logging()` (ya existe en `config/logger.py`) y dejar que `shared/infrastructure/api/error_handlers.py` capture excepciones no controladas como `500 GEN-500` sin ocultarlas como falsos 404. |
| **Inconsistencia de modelado (no-OWASP pero crítico)** | Referencias mixtas: `activos.area_id` es ObjectId pero `usuarios.area_id` es string; `tickets.responsables` referencia por email mientras `solicitante_id` referencia por ObjectId. | Regla única y consistente en el nuevo sistema: **toda referencia a otra entidad se guarda como su `_id` (ObjectId)**, nunca por nombre ni por email. Desnormalizar solo `{id, nombre}` cuando `.claude/MONGODB_MODELING.md` lo justifique. |

---

## 4. Datos que deben preservarse (plan de migración de datos)

No todo se reconstruye desde cero. Se preserva:

1. **Áreas** (17 registros) — se migran tal cual, generando nuevos `_id` si la colección se remodela, pero conservando `nombre` exacto para no romper reportes/hábitos del equipo.
2. **Usuarios administradores** (2 registros) — se migran preservando `email`/`identificacion`, remapeando su rol legacy (`super_admin`/`admin`) al nuevo catálogo de roles (§6.6). Las contraseñas hasheadas con bcrypt son compatibles y pueden reutilizarse sin forzar reset, salvo que se decida rotar por política.
3. **Categorías** (7 registros) — se migran tal cual.
4. **Estados** (3 registros: Bueno/Excelente/Regular) — **no se descartan**, pero se re-conceptualizan: en el legacy `estado` mezclaba "condición física" con lo que el encargo llama "estado del ciclo de vida" (Disponible/Prestado/En mantenimiento/Dado de baja/Perdido/Dañado). **Decisión de diseño a validar en Fase 0 del módulo `activos`:** separar en dos campos — `condicion` (catálogo preservado: Bueno/Excelente/Regular) y `estado_ciclo_vida` (nuevo enum: Disponible/Prestado/En mantenimiento/Dado de baja/Perdido/Dañado). Esto evita perder el dato ya cargado y a la vez cumple el requerimiento del encargo.

**Mecánica de migración recomendada:** un script de migración (fuera de `modules/`, en `scripts/` o `tools/` del proyecto nuevo) que lee la Mongo legacy y escribe en la Mongo nueva vía los repositorios concretos de cada módulo ya construido (nunca insertando documentos "a mano" con forma arbitraria) — así la migración pasa por las mismas reglas de validación que usará la aplicación en producción. Este script se escribe **después** de que el módulo destino exista, no antes.

---

## 5. Mapeo conceptual: ticket → solicitud

| Legacy (`ticket`) | Nuevo (`solicitud`) |
|---|---|
| `tipo`: `SOPORTE_TECNICO`, `MANTENIMIENTO`, `CAMBIO`, `PAPELERIA` | `tipo`: `mantenimiento`, `cambio`, `ajuste`, `reporte_dano`, `reporte_perdida` (nuevo catálogo, no es 1:1 con el legacy) |
| `estado`: 5 valores, transición libre | `estado`: máquina de estados **con transiciones válidas explícitas** (a diseñar en Fase 2), incluyendo estados de aprobación/rechazo que hoy no existen |
| `responsables` (emails, manual) | Asignación **automática** por tipo → área (Mantenimiento → Área Mantenimiento; Cambio → Área Tecnología; Ajuste → área correspondiente al activo), no elegida a mano por quien crea la solicitud |
| Sin concepto de aprobación | Aprobación explícita como parte del flujo (quién aprueba, con qué rol, con qué resultado) |
| `activos_ids` (bug de tipos) | `activo_id` único por solicitud (el encargo habla de "el activo relacionado", singular) — a confirmar en Fase 0 |
| `seguimiento` (array embebido) | Se conserva el patrón de auditoría/seguimiento, pero como historial propio del módulo, evaluando si debe ser colección separada (ver §7.3) |
| Restricción "solo activos asignados al usuario" | El encargo exige explícitamente: *"Los usuarios deben poder crear solicitudes relacionadas únicamente con los activos o elementos que tienen asignados"* — esta validación **no existe en el legacy** y debe construirse desde cero como regla de dominio |

---

## 6. Módulos del nuevo sistema

Cada módulo sigue la estructura de `modules/<modulo>/` de `.claude/ARCHITECTURE.md`, usando `modules/tareas/` como plantilla. Resumen de qué se hereda del legacy y qué es diseño nuevo:

### 6.1 `catalogos` — Áreas, Categorías, Estados/Condición

- **Se hereda:** estructura de campos, datos ya cargados (§4).
- **Nuevo:** unicidad de `nombre` garantizada con índice `uq_` real en Mongo (en el legacy la unicidad solo se validaba a mano, sin índice, con riesgo de condición de carrera).
- **Validación de integridad referencial diferida:** la regla "no se puede eliminar si está en uso" requiere consultar `activos`, que todavía no existe en el orden de construcción (§8.2). Se construye `catalogos` con borrado físico simple (sin verificar uso, porque hoy no hay nada que pueda usarlo) y se agrega la validación como mejora deliberada cuando `activos` exista — sin inventar una abstracción prematura para un módulo que aún no está.
- **Nota de alcance (Fase 0):** decidir si Área/Categoría/Estado viven en un único módulo `catalogos` (por ser simples y sin lógica propia compleja) o en tres módulos separados. Dado que ninguno tiene lógica de negocio propia relevante más allá de CRUD + unicidad, se recomienda **un solo módulo** para evitar sobre-fragmentación, revisándolo explícitamente en la Fase 0 de este módulo.
- **Extensión (Fase 0 de `activos`):** el encargo original no detallaba la estructura física de ubicación; al diseñar `activos` surgió que la organización real tiene **sedes** (Prado, Bosa) y, dentro de cada una, **lugares** tipados (bodega, baño, espacio común, oficina, exterior). Se agregaron `Sede` y `Lugar` como dos sub-entidades más de `catalogos` (mismo patrón CRUD independiente que Área/Categoría/Condición), con `Lugar` referenciando `sede_id` y unicidad de nombre **por sede** (no global). `activo.ubicacion` pasa a ser `sede_id` + `lugar_id` (referencias), no texto libre embebido como en el legacy. Se sembraron Prado/Bosa + bodega/baño/exterior de cada una; los ~10 espacios comunes y ~20 oficinas se cargan después desde la API.

### 6.2 `usuarios` — Usuarios, autenticación y roles

- **Se hereda:** hashing bcrypt, JWT como mecanismo, los 2 usuarios admin ya cargados.
- **Nuevo por completo:** enum cerrado de roles, autorización centralizada, protección A07 (rate limiting, bloqueo de cuenta), consistencia de `area_id` como `ObjectId`.
- **Importante:** el `shared/` de la plantilla actual **solo** trae autenticación *servicio-a-servicio* (Cloud Run↔Cloud Run vía Google ID tokens, ver `shared/infrastructure/gcp/authentication/`), **no** autenticación de usuario final. La autenticación con roles de empleados es responsabilidad de este módulo nuevo, no algo que ya provea `shared/`.
- **Roles nuevos vs. legacy:**

| Rol legacy | Rol nuevo (encargo) |
|---|---|
| `super_admin` | Administrador General |
| `admin` | Administrador General (o Administrativo, según el caso concreto — a confirmar) |
| `empleado` | Empleado / Jefe de Área (según si tiene personas a cargo) |
| *(no existía)* | Tecnología |
| *(no existía)* | Mantenimiento |

### 6.3 `activos` (incluye "elementos")

- **Se hereda:** casi todo el modelo de campos, la lógica de creación/edición/validación de relaciones.
- **Decisión pendiente de Fase 0:** el encargo agrupa "Activos Fijos" y "Elementos" bajo el mismo set de campos — validar con el usuario si son la misma entidad (quizá diferenciada por un campo `tipo: activo_fijo | elemento` o por umbral de `valor`) o si ameritan sub-módulos separados.
- **Nuevo:** campo `valor` (ausente en legacy), `fecha_adquisicion` explícita, separación `condicion` / `estado_ciclo_vida` (§4), `historial` como colección propia en vez de array embebido (§7.3), corrección del bug de comparación de tipos en el cálculo de cambios.

### 6.4 `solicitudes` (ex-tickets)

- **Se hereda:** noción de tipo + estado + seguimiento como base conceptual.
- **Nuevo:** enrutamiento automático por tipo→área, motor de aprobación, restricción "solo activos asignados al usuario", notificación por correo funcional (la del legacy está rota), matriz de transición de estados explícita.

### 6.5 `mantenimientos`

- **100% diseño nuevo** (sin lógica legacy real). Debe modelar preventivo/correctivo, técnico responsable, costo, documentos soporte, evidencias, y el sistema de alertas/recordatorios con frecuencia configurable descrito en el encargo.
- Depende de `activos` (referencia) y de la capacidad de notificación (`shared`, ver §6.7).

### 6.6 `movimientos`

- **100% diseño nuevo.** Tres sub-flujos con complejidad muy distinta:
  1. Préstamo entre usuarios (2 pasos: solicitud + aprobación del responsable actual).
  2. Salida para eventos/campañas (5 pasos secuenciales con aprobación doble + comprobante descargable — el flujo más complejo del sistema).
  3. Baja o destrucción (flujo controlado con aprobación administrativa).
- **Recomendación de Fase 0:** evaluar si estos 3 sub-flujos son un único módulo `movimientos` con un tipo discriminante, o si el flujo 2 (por su complejidad y generación de documento) amerita tratarse como su propio contexto. Se decide explícitamente antes de modelar, no por defecto.

### 6.7 Notificaciones — capacidad transversal, no necesariamente módulo con rutas propias

Todos los módulos anteriores (`solicitudes`, `movimientos`, `mantenimientos`) necesitan enviar correos en eventos equivalentes (creación, aprobación, rechazo, recordatorio). Según la regla de `.claude/ARCHITECTURE.md` ("¿lo usan varios módulos? → `shared/`"), el **envío** de correo se modela como un puerto en `shared/application/` (p. ej. `NotificadorPort`) con su adaptador Gmail/SMTP en `shared/infrastructure/`, replicando el patrón ya usado para `shared/application/service_invocation/` + `shared/infrastructure/gcp/cloud_run/`. Si el frontend necesita **listar/auditar** notificaciones enviadas (bandeja, historial), eso sí amerita un módulo propio `modules/notificaciones/` que solo registra el log y consume el puerto compartido para enviar. Esta división (capacidad compartida vs. módulo de auditoría) se confirma en Fase 0.

### 6.8 `dashboard`

- **No existe en absoluto en el legacy** (archivo vacío, no montado). Es un módulo de solo lectura que agrega datos de `activos`, `solicitudes`, `mantenimientos`, `movimientos` — se construye **al final**, cuando esos módulos ya existen, siguiendo las convenciones de pipelines de `.claude/MONGODB_QUERIES.md`.

---

## 7. Consideraciones transversales de diseño

### 7.1 Auditoría (`creado_por` / `actualizado_por`)

Todo módulo nuevo sigue el patrón de `.claude/MONGODB_MODELING.md`: nunca `created_by_id` suelto, siempre `creado_por: {id_persona, nombre, fecha}` embebido, para poder mostrar "Creado por X el Y" sin lookup adicional.

### 7.2 Referencias consistentes

Regla única para todo el proyecto nuevo (corrige la inconsistencia legacy de §3): toda relación entre colecciones se guarda por `_id` (ObjectId), nunca por nombre ni por email. Se desnormaliza `{id, nombre}` solo cuando se cumplen las tres condiciones de `.claude/MONGODB_MODELING.md` (se muestra en listados frecuentes, cambia raramente, la desactualización es aceptable).

### 7.3 Historial: colección propia, no array embebido

El legacy embebe `historial` dentro de cada `activo`, generándolo automáticamente al comparar campos en cada update. Esto choca con las señales de alerta de `.claude/MONGODB_MODELING.md`: es un array que **puede crecer sin límite previsible** y que probablemente se necesite **consultar independientemente** del activo (p. ej. "todos los cambios de este mes", "todo el historial de un usuario"). **Recomendación:** modelar `historial` como colección propia (posiblemente dentro de `shared/` si se decide que aplica a más de una entidad — activos, solicitudes, movimientos podrían compartir el mismo patrón de auditoría de cambios), con índice compuesto `(entidad_tipo, entidad_id, fecha)`. Esto se confirma explícitamente en la Fase 1 del módulo correspondiente.

### 7.4 Estados y transiciones

Ningún módulo nuevo debe repetir el patrón legacy de "cualquier estado a cualquier estado sin validación". Cada entidad con estados (`activo.estado_ciclo_vida`, `solicitud.estado`, `movimiento.estado`, `mantenimiento.estado`) debe declarar su matriz de transiciones válidas como parte del diseño de dominio (Fase 2 de `WORKFLOW.md`), y esa matriz se valida en el servicio de aplicación, no en la ruta HTTP.

### 7.5 Archivos y evidencias (fotos, fichas técnicas, comprobantes)

El legacy solo guarda URLs sueltas (`foto_url`, `ficha_tecnica_url`) sin un servicio de almacenamiento real (`file_service.py` está vacío). El nuevo sistema necesita decidir explícitamente (Fase 0 del módulo `activos` o de un módulo `shared` de almacenamiento) dónde se suben evidencias/comprobantes (GCS, por ejemplo, dado que ya se usa GCP en `shared/infrastructure/gcp/`) antes de modelar los campos que solo guardan la URL resultante.

---

## 8. Modo de trabajo — cómo se construye cada módulo

### 8.1 Principio general

Cada módulo de la lista de §6 se construye **uno a la vez**, siguiendo íntegramente las 4 fases de `.claude/WORKFLOW.md`:

```
Fase 0 — Alcance acordado por escrito (preguntas de WORKFLOW.md, incluyendo las decisiones pendientes marcadas en este documento con "Decisión de Fase 0")
Fase 1 — Modelado Mongo (.claude/MONGODB_MODELING.md), schema confirmado antes de escribir código
Fase 2 — Diseño de dominio y servicios, presentado para revisión antes de programar
Fase 3 — Construcción siguiendo .claude/TEMPLATE.md (domain → application → infrastructure → bootstrap), con tests unitarios junto a cada servicio
Fase 4 — .claude/SOLID_CHECKLIST.md completo antes de dar el módulo por cerrado
```

No se salta de fase. No se construyen dos módulos en paralelo salvo que ambos ya tengan su Fase 0/1/2 aprobadas por separado.

### 8.2 Orden recomendado de construcción

El orden sigue dependencias reales (un módulo no debe referenciar IDs de un módulo que todavía no existe) y prioriza primero lo que tiene datos legacy que preservar.

**Nota de dependencia cruzada (detectada en Fase 0 de `catalogos`):** `catalogos` necesita protección por rol (`admin`/`super_admin`) en sus endpoints de escritura, lo cual requiere que exista autenticación de usuario final con roles — pero `usuarios.area_id` referencia a `catalogos`. Se resuelve invirtiendo el orden: **`usuarios` se construye primero**, modelando `area_id` como referencia `ObjectId` opcional **sin validar su existencia todavía** (esa validación se agrega como mejora una vez que `catalogos` exista). Así `catalogos` nace protegido por rol desde el día uno.

1. **`usuarios`** (autenticación end-user, roles, CRUD de empleados) — sin dependencias de datos de otro módulo; `area_id` se modela como referencia opcional sin FK validada aún.
2. **`catalogos`** (áreas, categorías, condición) — depende de `usuarios` para proteger por rol sus endpoints de escritura. Datos legacy a migrar en cuanto este módulo cierra su Fase 4.
3. **Capacidad de notificaciones** en `shared/` (puerto + adaptador Gmail) — se necesita antes de que cualquier módulo de negocio dispare correos.
4. **`activos`** — depende de `catalogos` y `usuarios`.
5. **`solicitudes`** — depende de `activos` y `usuarios`; primer módulo con máquina de estados y aprobación real.
6. **`mantenimientos`** — depende de `activos`, `usuarios`, notificaciones.
7. **`movimientos`** — depende de `activos`, `usuarios`, notificaciones; empezar por el sub-flujo más simple (préstamo entre usuarios) antes que el de eventos/campañas (5 pasos) o la baja/destrucción.
8. **Historial/auditoría como colección propia** (§7.3) — se puede introducir en paralelo con `activos` si se confirma en Fase 1 de ese módulo, o como pieza de `shared/` reutilizada por los módulos siguientes.
9. **`dashboard`** — al final, cuando ya existen datos reales en los módulos anteriores para agregar.

### 8.3 Migración de datos legacy

Se ejecuta **módulo por módulo**, inmediatamente después de que cada módulo pasa su Fase 4 (checklist SOLID) — con una excepción importante por la inversión de orden de §8.2: el **código** de `usuarios` se construye antes que `catalogos`, pero la **migración de datos** de los 2 usuarios admin (que referencian el área "Dirección") se ejecuta *después* de migrar `catalogos`, para que su `area_id` apunte a un documento de área real ya existente, no a un ID huérfano. Es decir: orden de construcción de código ≠ orden de migración de datos. El resto de módulos migra sus datos en el mismo orden en que se construyen, sin esta excepción.

### 8.4 Definición de "módulo terminado"

Un módulo se considera cerrado cuando cumple, en este orden:

1. Alcance de Fase 0 documentado y aprobado.
2. `.claude/SOLID_CHECKLIST.md` completo (arquitectura, ubicación de código, API, MongoDB, tests, `register_module`).
3. Todas las reglas de negocio relevantes de este documento (secciones 3, 5, 6 y 7 aplicables a ese módulo) están cubiertas por al menos una prueba unitaria.
4. Si el módulo reemplaza datos legacy: el script de migración correspondiente corrió exitosamente contra un entorno de prueba.

---

## 9. Estado de avance

| Módulo | Fase 0 | Fase 1 | Fase 2 | Fase 3 | Fase 4 |
|---|---|---|---|---|---|
| `usuarios` | ✅ Aprobado | ✅ Aprobado | ✅ Aprobado | ✅ Construido (código + 25 tests) | ✅ Revisado |
| `catalogos` (Área/Categoría/Condición) | ✅ Aprobado | ✅ Aprobado | ✅ Aprobado | ✅ Construido (código + 54 tests) | ✅ Revisado |
| `catalogos` (Sede/Lugar, extensión) | ✅ Aprobado | ✅ Aprobado | ✅ Aprobado | ✅ Construido (código + 40 tests) | ✅ Revisado |
| `activos` | ✅ Aprobado | ✅ Aprobado | ✅ Aprobado | ✅ Construido (código + 56 tests) | ✅ Revisado |
| `solicitudes` | ✅ Aprobado | ✅ Aprobado | ✅ Aprobado | ✅ Construido (código + 57 tests) | ✅ Revisado |
| Resto de módulos (§6.5–§6.8: mantenimientos, movimientos, dashboard) | Pendiente | — | — | — | — |

**Suite completa: 292 tests pasando.**

**Fase 0 de `activos` — decisiones ya cerradas:**

| Decisión | Resultado |
|---|---|
| Activos vs Elementos | Una sola entidad `Activo` con campo `tipo: activo_fijo \| elemento` |
| Transiciones de `estado_ciclo_vida` | Matriz de transiciones válidas (no libres) — a definir en Fase 2 |
| Almacenamiento de archivos | Solo URL por ahora (`foto_url`/`ficha_tecnica_url`); sin mecanismo de subida propio todavía |
| Historial de cambios | Colección propia desde el inicio (confirma §7.3), no array embebido |
| `valor` y `fecha_adquisicion` | Obligatorios |
| `ubicacion` | `sede_id` + `lugar_id` (catálogos `Sede`/`Lugar`, ver §6.1), no texto libre |
| `complementos` | Se mantienen embebidos (lista de accesorios), igual que el legacy |
| Validaciones diferidas de `catalogos`/`usuarios` | Se activan como parte de la Fase 3 de `activos` (ver próximos pasos) |

**Detalles de lo construido en `activos`:**
- `Activo` (con `tipo`, `estado_ciclo_vida`, referencias por `_id` a `catalogos` y `usuarios`, `complementos` embebidos) + `EntradaHistorialActivo` (colección propia `activos_historial`, confirma §7.3).
- Matriz de transiciones de `estado_ciclo_vida` implementada en `domain/transiciones.py`, validada por `CambiarEstadoActivoService` (error `ACT-003` si la transición no es válida).
- **Sin borrado físico**: un activo que termina su vida útil pasa a `dado_de_baja` (estado terminal), preservando su registro — decisión explícita que mejora sobre el `DELETE` físico del legacy.
- `ActualizarActivoService` registra automáticamente en `activos_historial` cada cambio de `responsable_id`/`area_id`/`condicion_id`/`sede_id`/`lugar_id`, comparando entidades de dominio ya normalizadas (corrige el bug legacy de comparar `ObjectId` vs `str`).
- Campo `valor` almacenado como `Decimal128` en Mongo (vía `bson.decimal128`), mapeado a `Decimal` de Python en el dominio.
- Índices: `uq_numero_inventario`, `idx_area_id`, `idx_categoria_id`, `idx_responsable_id`, `idx_condicion_id`, `idx_estado_ciclo_vida`, `idx_sede_id`, `idx_lugar_id` en `activos`; `idx_activo_id_fecha` compuesto en `activos_historial`.

**Validaciones diferidas — activadas:**
- `catalogos`: `EliminarAreaService`/`EliminarCategoriaService`/`EliminarCondicionService`/`EliminarLugarService` ahora consultan un nuevo puerto `VerificadorUsoEnActivosPort` (adaptador Mongo que consulta la colección `activos` **por nombre**, sin importar el código de `modules.activos`, para no acoplar los módulos) y bloquean el borrado con un error `CAT-01{3,4,5,6}` si hay algún activo asociado.
- `usuarios`: `RegistrarUsuarioService`/`ActualizarUsuarioService` ahora validan `area_id` contra un nuevo puerto `VerificadorAreaPort` (mismo patrón de adaptador Mongo por nombre de colección), con error `USR-006` si el área no existe.
- Ambas validaciones se probaron contra el Mongo local real: se creó un activo de prueba referenciando un área real migrada, se confirmó que `EliminarAreaService` bloquea su borrado (`CAT-013`), y se confirmó `VerificadorAreaPort.existe()` contra un área real y una inexistente. El activo de prueba se eliminó después de verificar.

**Detalles de lo construido en `usuarios`:**
- `shared/domain/entities/audit.py` (`AuditPersona`, reutilizable por todos los módulos futuros).
- `shared/application/user_auth/` + `shared/infrastructure/security/verificador_token_usuario_jwt.py` + `shared/infrastructure/api/dependencies/user_authentication.py` (`requiere_usuario_autenticado`, `requiere_rol(*roles)`) — verificación de JWT reutilizable por todos los módulos.
- `modules/usuarios/` completo (domain, application con 6 servicios, infrastructure con Mongo + bcrypt + JWT, bootstrap registrado en `shared/bootstrap/application.py`).
- Índices Mongo (`uq_email`, `uq_identificacion`, `idx_area_id`, `idx_rol`) creados en el arranque de la app (`lifespan`).
- Nuevas dependencias: `bcrypt`, `python-jose` (agregadas a `requirements.txt`); nueva configuración `JWT_SECRET_KEY`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES` (`config/settings.py`, `.env.example`).

**Detalles de lo construido en `catalogos`:**
- Tres sub-entidades independientes (`Area`, `Categoria`, `Condicion` — renombrada desde "estado"), cada una con su propio domain/ports/services/repository/routes, siguiendo el patrón 1:1 de `modules/tareas` (decisión explícita: sin abstracción genérica compartida, ver §6.1).
- Tres colecciones Mongo (`areas`, `categorias`, `condiciones`), cada una con índice único `uq_nombre`, creado en el `lifespan` de la app.
- CRUD completo (crear/listar/obtener/actualizar/eliminar) por sub-entidad, protegido con `requiere_rol("administrador_general")` para escritura y `requiere_usuario_autenticado` para lectura.
- `Condicion` valida formato de color hexadecimal tanto en el schema HTTP como en el dominio (para que la validación tampoco se salte desde un script de migración).
- **Diferido en su momento, activado al construir `activos`** (ver detalle en §11): la validación "no se puede eliminar si está en uso".

**Detalles de lo construido en `catalogos` (extensión Sede/Lugar):**
- `Sede` (nombre único global) y `Lugar` (nombre único **por sede**, con `tipo` enum: bodega/baño/espacio_comun/oficina/exterior), cada uno con su propio domain/ports/services/repository/routes.
- Colección `lugares` con índice compuesto único `uq_sede_nombre` (`sede_id`+`nombre`) e índice `idx_sede_id`; colección `sedes` con `uq_nombre`.
- `EliminarSedeService` valida que la sede no tenga lugares asociados (`SedeEnUsoError`, CAT-010) — posible de implementar ya porque Sede y Lugar están en el mismo módulo, a diferencia del caso Área/Categoría/Condición/Lugar vs. `activos`.
- `scripts/sembrar_sedes_lugares.py`: siembra Prado y Bosa, cada una con lugares bodega/baño/exterior. Ejecutado y verificado contra el Mongo local real (idempotente).

**Detalles de lo construido en `solicitudes`:**
- `Solicitud` con 5 tipos (`mantenimiento`, `cambio`, `ajuste`, `reporte_dano`, `reporte_perdida`), enrutamiento automático: `mantenimiento`→rol `mantenimiento`, `cambio`→rol `tecnologia` (no existe una `Area` "Mantenimiento" real en el catálogo, así que estos dos se asignan por **rol**, no por área), `ajuste`/`reporte_dano`/`reporte_perdida`→`area_id` del activo.
- `creado_por` cumple doble función: auditoría estándar **y** identidad del solicitante (no se duplica en un campo `solicitante_id` aparte).
- Matriz de transición propia: `pendiente→{en_proceso, rechazada}`, `en_proceso→{resuelta, rechazada}`, `resuelta→{cerrada}`, `cerrada`/`rechazada` terminales.
- Regla de permisos pura en `domain/permisos.py::puede_gestionar` (solicitante, rol/área asignada, o `administrador_general`) — reutilizada tanto por `CambiarEstadoSolicitudService` como por `AgregarSeguimientoSolicitudService`.
- **Cambio técnico transversal:** se agregó el claim `area_id` al JWT (`JWTEmisorToken`, `VerificadorTokenUsuarioJWT`, `IdentidadUsuarioAutenticada`) para poder validar "¿pertenece el usuario al área asignada?" sin que `solicitudes` tenga que consultar `usuarios`.
- **Puerto compartido nuevo:** `shared/application/notifications/ports.py::NotificadorPort`, con adaptador `LogNotificador` (solo registra en log) en `shared/infrastructure/notifications/`. Los destinatarios son identificadores lógicos (`"rol:mantenimiento"`, `"area:<id>"`, `"usuario:<id>"`), no emails resueltos — la resolución real queda para cuando se construya el adaptador Gmail.
- **Puerto cruzado hacia `activos`:** `ActivoResumenPort` (mismo patrón de consulta por nombre de colección, sin importar código de `modules.activos`) para validar que el activo existe y obtener su `responsable_id`/`area_id`.
- Verificado de punta a punta contra el Mongo local real: activo + solicitud reales, enrutamiento por rol confirmado, notificación (stub) registrada en el log, transición de estado aplicada. Datos de prueba eliminados después.

## 10. Migración de datos — ejecutada y verificada

`scripts/migrar_catalogos.py` y `scripts/migrar_usuarios.py` (más el helper `scripts/_legacy_db.py`) ya existen y se ejecutaron contra el Mongo local real:

- 17 áreas, 7 categorías y 3 condiciones migradas a la base `activos_fijos` (nueva).
- 2 usuarios admin migrados, con `area_id` resuelto correctamente a la nueva área "Dirección", rol legacy `admin`/`super_admin` mapeado a `administrador_general`, y **hash de password preservado tal cual** (bcrypt/passlib legacy es compatible con `bcrypt.checkpw` del nuevo sistema — verificado contra la contraseña real).
- Idempotencia verificada: re-ejecutar ambos scripts no duplica nada.
- Índices (`uq_nombre` × 3, `uq_email`/`uq_identificacion`/`idx_area_id`/`idx_rol`) creados manualmente una vez, ya que hasta ahora la app nunca se había arrancado en este entorno (los scripts de migración no arrancan el `lifespan` completo).
- Se creó un `.env` local (gitignored) apuntando a `MONGO_DB=activos_fijos`, distinto tanto del legacy (`GESTIONACTIVOSFIJOS`) como de otras bases no relacionadas encontradas en el mismo Mongo local (`inventario_db`, `codex` — de otros proyectos, no tocadas).

**Hallazgo de seguridad (no bloqueante, informativo):** `BACKEND VIEJO/app/.env` tiene una contraseña de aplicación de Gmail (`GMAIL_APP_PASSWORD`) en texto plano. No es un secreto que este proyecto vaya a reutilizar (el sistema de notificaciones se diseña desde cero, ver §6.7), pero como recomendación general esa credencial legacy debería rotarse si se sigue usando en algún lado.

## 11. Próximos pasos inmediatos

`solicitudes` está completo (Fases 0–4). Siguiente módulo en el orden de §8.2: `mantenimientos`.

1. Iniciar Fase 0 de `.claude/WORKFLOW.md` para `mantenimientos`: preventivo/correctivo, técnico responsable, costo, documentos soporte, evidencias, y el sistema de alertas/recordatorios con frecuencia configurable del encargo.
2. Decidir si `mantenimientos` se dispara únicamente desde una `solicitud` de tipo `mantenimiento` ya aprobada/en proceso, o si también puede crearse de forma independiente (mantenimiento preventivo programado sin que medie una solicitud).
3. Reutilizar el patrón ya establecido: `ActivoResumenPort`-like adapter hacia `activos` si se necesita, `NotificadorPort` ya existente en `shared/` para las alertas.
4. Después, en el orden de §8.2: `movimientos` (los 3 sub-flujos: préstamo entre usuarios, salida para eventos, baja/destrucción — empezar por el más simple), y finalmente `dashboard`.
