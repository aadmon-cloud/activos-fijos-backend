# MIGRATION_PLAN.md

> Guía oficial de migración incremental del legacy `inventarios/` (FastAPI + MongoDB monolítico,
> sin arquitectura de capas) hacia la arquitectura hexagonal de este repositorio
> (`infrastructure → application → domain`, ver `.claude/ARCHITECTURE.md`).
>
> Este documento es un plan **vivo**: se actualiza a medida que se resuelven dudas o se
> completan fases. No contiene código. La migración se ejecuta módulo por módulo, capa por
> capa, archivo por archivo — nunca de forma masiva.

---

## Decisiones de alcance ya acordadas

Estas decisiones fueron tomadas explícitamente con el desarrollador antes de diseñar los
módulos y aplican a **todo** el plan:

| Decisión | Resuelto | Detalle |
|---|---|---|
| Frontend Jinja2 / HTML / estáticos | **Fuera de alcance** | El legacy sirve páginas server-rendered (`app/templates/*.html`) y estáticos (`app.js`, `style.css`, `qr-scanner.js`) desde el mismo backend. El backend nuevo es **solo API JSON** (`/api/...`). Se asume un frontend externo (React/Vue u otro) que consumirá esta API. Ninguna ruta HTML, template o estático legacy se migra. |
| Almacenamiento de archivos (imágenes, PDFs firmados, plantillas Excel) | **Disco local por ahora** | Se mantiene almacenamiento en filesystem del servidor, igual que el legacy, detrás de un puerto de aplicación (p. ej. `StorageRepositoryPort`) para poder reemplazarlo por MinIO/GCS más adelante sin tocar `domain/`/`application/`. |
| Google OAuth | **Incluido desde el inicio** | El módulo `auth` se diseña desde la Fase 2 contemplando dos vías de autenticación: email/password (JWT propio) y Google OAuth, no solo password. |

Cualquier decisión nueva que surja durante el análisis de un módulo específico se añade a la
tabla de esa sección como "Decisiones pendientes" y se resuelve antes de pasar a Fase 2 de
ese módulo.

---

# Estado general de la migración

## Módulos identificados

| # | Módulo (nuevo) | Responsabilidad de negocio | Colección(es) Mongo |
|---|---|---|---|
| 1 | `auth` | Autenticación (email/password + Google OAuth), roles, gestión de usuarios | `users` |
| 2 | `productos` | Catálogo de productos, códigos de barras/QR, imágenes, carga/descarga masiva Excel | `productos` |
| 3 | `ubicaciones` | Stock físico por ubicación de cada producto (crear, actualizar, eliminar, transferir) | `ubicaciones` |
| 4 | `mercados_predefinidos` | Catálogo de "kits" predefinidos (Mercado Básico/Grande) | `mercados_predefinidos` |
| 5 | `reservas` | Carrito de reserva temporal de stock por sesión, para salidas pendientes de confirmar | `reservas` |
| 6 | `movimientos` | Entradas/salidas de inventario (individuales, múltiples, kits, por mercado), remisiones, comprobantes PDF, exportación Excel | `movimientos`, `contadores` |
| 7 | `aprobaciones_pendientes` | Flujo de aprobación de entradas/salidas por `super_admin` antes de aplicarlas al inventario | `entradas_pendientes`, `salidas_pendientes` |
| 8 | `inventario_reportes` | Dashboard, reportes agregados, productos bajo stock, historial por producto | *(lectura de `productos`/`movimientos`, sin colección propia)* |

**Nota:** los 8 módulos son *bounded contexts* de negocio propuestos a partir del análisis del
legacy. `crud.py` (1489 líneas) y `models.py`/`schemas.py` mezclan las responsabilidades de
los 8 dominios en archivos únicos — no existe una equivalencia 1 a 1 entre archivo legacy y
módulo nuevo en ningún caso.

## Prioridad de migración

Orden recomendado, basado en dependencias reales (no en facilidad ni en tamaño):

1. **`auth`** — depende de nadie. Todo lo demás depende de sus roles (`require_authenticated`,
   `require_super_admin`) y de su entidad `Usuario` (autoría de movimientos, aprobaciones).
2. **`productos`** — catálogo base. Referenciado por todos los módulos de inventario.
3. **`ubicaciones`** — depende de `productos` (un producto debe existir para tener ubicaciones).
4. **`mercados_predefinidos`** — depende de `productos` (referencia productos por código), independiente de `movimientos`/`ubicaciones`.
5. **`reservas`** — depende de `productos` y `ubicaciones` (calcula stock disponible = físico − reservado).
6. **`movimientos`** — depende de `productos`, `ubicaciones`, `reservas`, `mercados_predefinidos` y `auth`. Es el módulo más complejo y el que más lógica de negocio concentra.
7. **`aprobaciones_pendientes`** — depende de `movimientos` (al aprobar, debe generar el movimiento real) y `auth`.
8. **`inventario_reportes`** — solo lectura agregada sobre `productos` y `movimientos`; puede migrarse en cualquier momento después de tener 2 y 6 listos.

## Dependencias entre módulos

```
auth ──────────────┬─────────────┬──────────────┬───────────────────┐
                    ▼             ▼              ▼                   ▼
                productos    (roles usados   (autoría de         (aprobador de
                    │          por todos)     movimientos)        pendientes)
                    ▼
              ubicaciones ──────────┐
                    │                │
                    ▼                ▼
              mercados_predefinidos  reservas
                    │                │
                    └───────┬────────┘
                             ▼
                        movimientos ──────► aprobaciones_pendientes
                             │
                             ▼
                    inventario_reportes
```

## Candidatos a `shared/` (a confirmar por módulo, no decidido aún)

Detectados durante el análisis; **no se resuelven ahora** — se confirman en la Fase 2 del
primer módulo que los necesite, siguiendo la regla de `.claude/ARCHITECTURE.md`
(¿lo usan varios módulos?):

| Candidato | Origen legacy | Usado hoy por | ¿Por qué podría ir en `shared/`? |
|---|---|---|---|
| `StorageRepositoryPort` (archivos en disco) | subida de imágenes en `routers/productos.py`, PDFs en `routers/movimientos.py` | `productos`, `movimientos` | Mismo mecanismo de guardar/leer/eliminar archivos, dos módulos distintos lo necesitan |
| Generador de secuenciales (`generar_numero_remision`, colección `contadores`) | `crud.py::generar_numero_remision` | hoy solo `movimientos`, pero es un patrón genérico de contador atómico | Es infraestructura genérica (no reglas de negocio de inventario); podría generalizarse a "secuencia con prefijo" reutilizable |
| Envío de email (`core/email.py`) | `routers/auth.py` | hoy solo `auth` | Hoy es de un solo módulo → se queda en `auth/infrastructure` salvo que aparezca un segundo consumidor |
| ~~`get_current_user` / `require_role`~~ **RESUELTO** | `core/dependencies.py` | **todos** los routers protegidos | Decisión tomada en Fase 0 de `auth`: vive en `shared/infrastructure/api/dependencies/auth.py` desde el primer incremento, consumiendo un puerto expuesto por `auth`. Ver sección del módulo `auth`. |

---

# Módulo `auth`

## Objetivo

Autenticar usuarios (email/password y Google OAuth), emitir/validar JWT, gestionar roles
(`super_admin`, `admin`, `operativo`) y administrar el ciclo de vida de cuentas de usuario
(alta pública, alta administrativa, recuperación de contraseña, activar/desactivar, cambio de rol).

## Fase 0 — Alcance acordado (WORKFLOW.md)

Decisiones cerradas con el desarrollador antes de pasar a Fase 1 (modelado Mongo):

| Pregunta | Decisión |
|---|---|
| Alcance del **primer incremento** de construcción | Solo `LoginService` + `RegistrarUsuarioService` + roles (JWT, DTO de usuario, `MongoUsuarioRepository`, dependencia HTTP de usuario actual). Recuperación de password, Google OAuth y gestión admin de usuarios quedan diseñados en este documento pero se construyen en incrementos posteriores del mismo módulo — no en esta primera pasada. |
| Longitud mínima de contraseña | **8 caracteres** (endurece el mínimo de 6 vigente hoy en `UserLoginEmail`/`UserRegisterEmail`). |
| Colisión de `username` en registro | Se **mantiene** el comportamiento legacy: si el username (provisto o derivado del email) ya existe, se le agrega un sufijo aleatorio automático y el registro continúa. |
| Ubicación de la dependencia HTTP "usuario actual" (`get_current_user`/`require_role`) | **`shared/infrastructure/api/dependencies/auth.py` desde este primer incremento** (no se difiere), consumiendo un puerto expuesto por `auth`. Resuelve el candidato a `shared/` que había quedado abierto en la sección general del plan. |

Con esto, el **checklist de Fase 0** de `.claude/WORKFLOW.md` queda completo para el primer incremento de este módulo. Sigue la Fase 1 (modelado de la colección `users` en Moon Modeler / validación del schema Mongo) antes de escribir cualquier código.

## Fase 1 — Modelado MongoDB (colección `users`) — **APROBADA**

Estructura del documento:

| Campo | Tipo (bsonType) | Obligatorio | Notas |
|---|---|---|---|
| `_id` | objectId | sí | id técnico |
| `email` | string | sí | identificador natural de negocio (login), único, normalizado a minúsculas |
| `username` | string | sí | siempre poblado antes de persistir (provisto o derivado del email); único, con auto-sufijo si colisiona |
| `password_hash` | string | no | nulo si la cuenta es solo-Google (incremento futuro) |
| `rol` | string (enum: `super_admin`\|`admin`\|`operativo`) | sí | default `operativo` |
| `activo` | bool | sí | default `true`; sin historial (flag simple, no máquina de estados) |
| `email_verificado` | bool | sí | default `false` (lo usa el incremento futuro de verificación de email) |
| `google_id` | string | no | incremento futuro (Google OAuth) |
| `google_picture` | string | no | incremento futuro (Google OAuth) |
| `reset_password_token` | string | no | incremento futuro (recuperación de password) |
| `reset_password_expires` | date | no | incremento futuro |
| `creado_por` | object (`AuditPersona`) | sí | en auto-registro: `id_persona`/`nombre` = el propio usuario recién creado |
| `actualizado_por` | object (`AuditPersona`) | no | nulo hasta la primera actualización |

Embeber vs referenciar: colección raíz, sin subdocumentos que crezcan; solo aplica el patrón
de auditoría embebido (`AuditPersona`), por convención del proyecto.

Historial de estados: no aplica. `activo`/`email_verificado` son flags simples, sin
transiciones complejas ni necesidad de trazabilidad más allá de `actualizado_por`.

Índices propuestos:

| Nombre | Campos | Tipo | Responde a |
|---|---|---|---|
| `uq_users_email` | `email` (1) | único | login por email, duplicado en registro |
| `uq_users_username` | `username` (1) | único | duplicado de username |
| `idx_users_google_id` | `google_id` (1) | sparse | login/callback de Google — incremento futuro |
| `idx_users_reset_token` | `reset_password_token` (1) | sparse | flujo de reset password — incremento futuro |
| `idx_users_creado_fecha` | `creado_por.fecha` (-1) | normal | listado administrativo por antigüedad |

El validator se modela completo desde ahora (decisión Fase 1), aunque los campos de Google
OAuth y reset de password no tengan código que los use todavía — se sincronizan/activan
cuando se construya el incremento correspondiente.

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/routers/auth.py` | Login, registro, forgot/reset/change password, `/me`, init-users, flujo completo Google OAuth | `infrastructure/api/routes.py` (varios endpoints) + `application/services/` (un servicio por caso de uso) |
| `app/routers/admin.py` | CRUD de usuarios por `super_admin` (listar, crear, actualizar, eliminar) | `infrastructure/api/routes.py` (rutas bajo un sub-prefijo admin) + `application/services/` |
| `app/core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `decode_token` | `infrastructure/security/` (adaptador de hashing) + `application/ports/token_port.py` (puerto) + implementación JWT en infraestructura |
| `app/core/oauth.py` | Registro del cliente OAuth de Google (authlib) | `infrastructure/auth/google_oauth_client.py` |
| `app/core/dependencies.py` | `get_current_user`, `require_role`, `require_super_admin`, `require_authenticated` | Puerto (`UserRepositoryPort.buscar_por_id`) + servicio de validación en `auth`; el *dependency* de FastAPI reutilizable por otros módulos es candidato a `shared/infrastructure/api/dependencies/auth.py` (ver tabla de candidatos) |
| `app/core/email.py` | Envío de email de bienvenida y recuperación de contraseña | `infrastructure/email/smtp_email_sender.py` (implementa un `EmailSenderPort`) |
| `app/models.py::UserInDB`, `UserRole` | Modelo de usuario persistido | `domain/entities/usuario.py`, `domain/entities/rol.py` (o `Enum` en el mismo archivo) |
| `app/schemas.py::UserLogin/UserRegister/UserResponse/TokenResponse/UserLoginEmail/UserRegisterEmail/ForgotPasswordRequest/ResetPasswordRequest/ChangePasswordRequest` | Schemas HTTP de autenticación | `infrastructure/api/schemas.py` |

## Responsabilidades detectadas

- Login con email/password devolviendo JWT.
- Login con Google OAuth (redirect + callback), creación automática de usuario si no existe.
- Registro público de usuario (rol `operativo` por defecto).
- Recuperación de contraseña vía token con expiración (1h) + email.
- Cambio de contraseña autenticado.
- Gestión administrativa de usuarios (alta, edición de rol/estado, baja) — solo `super_admin`.
- Autorización basada en 3 roles jerárquicos.
- Inicialización de usuarios semilla (`init-users`) — **utilidad de bootstrap/seed, no endpoint de producción**.

## Domain

- **Entities**: `Usuario` (id, username, email, password_hash opcional —nulo si es solo-Google—, rol, activo, email_verificado, google_id opcional, fecha_creacion). `Rol` como enum de valores (`super_admin`, `admin`, `operativo`).
- **Errors**: credenciales inválidas, usuario inactivo, email ya registrado, username ya registrado, token de recuperación inválido/expirado, rol inválido, permisos insuficientes.

## Application

- **DTO**: entrada/salida por caso de uso (crear usuario, login, resultado de login con token, solicitar recuperación, resetear contraseña, cambiar contraseña, actualizar usuario administrativamente).
- **Ports**: `UsuarioRepositoryPort` (buscar por email/id/username/google_id, crear, actualizar, listar, eliminar), `PasswordHasherPort`, `TokenPort` (emitir/decodificar JWT), `EmailSenderPort`, `IdentityProviderPort` (abstracción sobre Google, para no acoplar `application/` a `authlib`).
- **Services** (una acción = una clase, según `.claude/CONVENTIONS.md`):
  - **Primer incremento (Fase 0 acordada):** `LoginService`, `RegistrarUsuarioService`.
  - **Incrementos posteriores del mismo módulo (diseñados aquí, no construidos aún):** `LoginConGoogleService`, `SolicitarRecuperacionPasswordService`, `RestablecerPasswordService`, `CambiarPasswordService`, `CrearUsuarioAdminService`, `ActualizarUsuarioAdminService`, `EliminarUsuarioAdminService`, `ListarUsuariosService`, `ObtenerUsuarioActualService`.

## Infrastructure

- **Persistence**: `MongoUsuarioRepository` (colección `users`), schema con índice único en `email` y en `username`.
- **API**: rutas `/api/auth/*` (login, register, forgot-password, reset-password, change-password, me, google, google/callback) y rutas administrativas `/api/auth/usuarios/*` o prefijo propio (a decidir en Fase 2 si comparten router o van separadas).
- **Security**: adaptador bcrypt para `PasswordHasherPort`, adaptador `python-jose` para `TokenPort`.
- **Auth externa**: adaptador `authlib` para `IdentityProviderPort` (Google).
- **Email**: adaptador SMTP para `EmailSenderPort`.

## Bootstrap

`register_module(app)` registra el router de auth. Debe exponer también (para consumo desde
`shared/`) la dependencia HTTP de "usuario actual" que usarán el resto de módulos — a definir
si vive en `auth/infrastructure/api/dependencies.py` y se importa desde `shared`, o si se
promueve directamente a `shared/infrastructure/api/dependencies/auth.py` (ver candidatos a shared).

## Validaciones

- Contraseñas: **mínimo 8 caracteres** (decisión Fase 0, endurece el mínimo de 6 vigente hoy).
- Username alfanumérico + guión bajo, normalizado a minúsculas.
- Email único; username único con **sufijo aleatorio automático si colisiona** (decisión Fase 0: se mantiene el comportamiento legacy).
- Rol debe ser uno de los 3 valores válidos.
- Confirmación de contraseña (`password == confirm_password`) en registro/reset/cambio.

## Riesgos

- ~~El legacy mezcla dos esquemas de usuario incompatibles...~~ **RESUELTO (verificado en código):** `UserLogin`/`UserRegister` (`schemas.py` líneas 13-21) no tienen ningún uso fuera de su propia definición (`grep` sin resultados en el resto del proyecto) — son código muerto. El contrato real y vigente es `UserLoginEmail`/`UserRegisterEmail`, que es el único que usa `routers/auth.py`. La entidad/DTO nueva se basa únicamente en la familia `*Email`.
- ~~Hay dos implementaciones de Google OAuth...~~ **RESUELTO (verificado en código):** `core/oauth.py` registra un cliente `authlib` (`google = oauth.register(...)`) que se importa en `auth.py` (`from app.core.oauth import google`) pero el objeto `google` **nunca se invoca** en todo el archivo (confirmado por `grep`). El flujo real y funcional es el manual: `google_login()` arma la URL de autorización a mano y `google_callback()` intercambia el código por token con `httpx` directamente. `core/oauth.py` es código muerto — el diseño nuevo del `IdentityProviderPort`/adaptador de Google se basa en el flujo manual (arma URL + intercambio de código vía HTTP), no en `authlib`.
- `SECRET_KEY` tiene un valor por defecto hardcodeado (`"tu-secret-key-muy-segura..."`) si la env var no existe — riesgo de seguridad si se replica tal cual.
- No hay invalidación/blacklist de tokens (logout es solo del lado del cliente).

## Utilidades reutilizables

- Ninguna utilidad pura reutilizable de este módulo aplica a otros dominios de negocio (hashing/JWT son infraestructura del propio módulo, expuesta como puerto consumido por `shared/`).

## Refactorizaciones recomendadas

- Unificar en un solo contrato de entrada/salida (eliminar la familia `UserLogin`/`UserRegister` si se confirma que es código muerto).
- Decidir una única implementación de Google OAuth (recomendado: la basada en intercambio manual de código, que es la que realmente funciona hoy) y eliminar la integración `authlib` no usada.
- Externalizar el rol por defecto y las reglas de unicidad de username como reglas de dominio explícitas, no side-effects silenciosos.

## Código que NO debe migrarse

- `app/core/oauth.py` completo (confirmado: código muerto, ver Riesgos).
- `schemas.py::UserLogin`, `UserRegister` (confirmado: código muerto, ver Riesgos).
- Los `print()` de depuración (`print(f"🔵 ...")`) — reemplazar por logging estructurado (`config/logger.py` ya existe en el proyecto nuevo).
- `SessionMiddleware` de Starlette — el flujo de Google confirmado (manual vía `httpx`) no la necesita.

## Checklist de migración

- [x] Domain — `Usuario`/`RolUsuario` (+ `AuditPersona` promovido a `shared/`), errores de dominio
- [x] Application — DTOs, `UsuarioRepositoryPort`/`PasswordHasherPort`/`TokenPort`, `LoginService`/`RegistrarUsuarioService`, 9 tests unitarios
- [x] Infrastructure — `MongoUsuarioRepository`, `BcryptPasswordHasher`, `JwtTokenAdapter`, schema Mongo `users` registrado
- [x] API — `POST /api/auth/login`, `POST /api/auth/registro`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 9 tests de servicios + verificación de app completa (imports, TestClient, suite 33/33)

**Pendiente para incrementos posteriores del mismo módulo** (fuera del alcance de este incremento, según Fase 0): recuperación de password, Google OAuth, gestión admin de usuarios.

## Incremento 2 — Recuperación de password (completo)

Construido siguiendo el mismo ciclo Fase 0 → 1 → 2 → 3:

- **Domain**: `Usuario.token_reset_valido()`, `generar_token_reset()`, `restablecer_password()`, `cambiar_password()` (métodos inmutables, mismo patrón `model_copy` que `Tarea.completar()` del módulo de ejemplo). Errores nuevos: `TokenRecuperacionInvalidoError` (400), `PasswordActualIncorrectaError` (401). Se reutilizó `ConfirmacionPasswordInvalidaError` para los dos casos de "las contraseñas no coinciden".
- **Application**: `EmailSenderPort` (nuevo, vive en `modules/auth/application/ports/`, no en `shared/`, porque hoy solo lo consume `auth` — ver tabla de candidatos a `shared/`). `UsuarioRepositoryPort` ampliado con `obtener_por_token_reset` y `actualizar`. Servicios: `SolicitarRecuperacionPasswordService`, `RestablecerPasswordService`, `CambiarPasswordService`. 11 tests nuevos (31 en total del módulo `auth`).
- **Infrastructure**: `SmtpEmailSender` (adaptador, best-effort — retorna `False` sin lanzar excepción si SMTP no está configurado o falla el envío, igual que el legacy). Settings nuevas: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL` (todas opcionales, vacías por defecto). Rutas `POST /api/auth/forgot-password` (pública), `POST /api/auth/reset-password` (pública), `POST /api/auth/change-password` (protegida con `require_authenticated`, ya disponible desde `shared/`).

### Bug real encontrado y corregido: comparación de fechas naive vs aware

Al probar `token_reset_valido()` contra Mongo real, `TypeError: can't compare offset-naive
and offset-aware datetimes`. Motor decodifica fechas de Mongo como `datetime` *naive* por
defecto; el proyecto usa `datetime.now(UTC)` (*aware*) en todo el dominio (`Usuario.crear`,
`AuditPersona.fecha`, etc.). **Este bug no era específico de `auth`** — afecta a cualquier
módulo futuro que compare una fecha leída de Mongo contra `datetime.now(UTC)`. Se corrigió
en `shared/infrastructure/persistence/mongo/database.py` agregando `tz_aware=True` al
`AsyncIOMotorClient`, en vez de parchear cada repositorio individualmente.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Se probó el flujo completo con un usuario de prueba real (creado y luego eliminado):
registro → forgot-password (token generado, email no enviado porque SMTP no está
configurado, comportamiento esperado) → lectura directa del token en Mongo (simulando el
email) → reset-password → login con password vieja (401) → login con password nueva (200)
→ change-password autenticado (200) → login con password más reciente (200) →
change-password con password actual incorrecta (401) → reset-password con token ya usado
(400, el token se limpia tras usarse). Los 9 casos se comportaron como se diseñó. `users`
(legacy) verificada intacta con sus 3 documentos originales antes y después.

### Checklist del incremento 2

- [x] Domain — métodos de transición en `Usuario` + 2 errores nuevos
- [x] Application — `EmailSenderPort`, ampliación de `UsuarioRepositoryPort`, 3 servicios, 11 tests
- [x] Infrastructure — `SmtpEmailSender`, settings SMTP, 3 rutas nuevas
- [x] Bugfix compartido — `tz_aware=True` en el cliente Mongo (afecta a todo el proyecto, no solo `auth`)
- [x] Verificación end-to-end contra `inventario_db` real, con limpieza de datos de prueba

## Incremento 3 — Google OAuth (completo)

- **Domain**: `Usuario.crear_desde_google()` (sin password, `email_verificado=True`) y `Usuario.vincular_google()` (para cuentas existentes por email/password que hacen login con Google por primera vez). Errores nuevos: `GoogleOAuthError` (502, falla de integración) y `GoogleOAuthNoConfiguradoError` (500, faltan credenciales).
- **Application**: `GoogleOAuthPort` (`construir_url_autorizacion`, `obtener_datos_usuario`), `DatosGoogleUsuarioDTO`. `UsuarioRepositoryPort` ampliado con `obtener_por_google_id`. Servicios: `IniciarLoginGoogleService` (wrapper delgado), `LoginConGoogleService` (busca por email o google_id → crea o vincula → verifica activo → emite JWT, reutilizando `ResultadoLoginDTO`). 8 tests nuevos.
- **Infrastructure**: `GoogleOAuthAdapter` — intercambio manual código→token→userinfo vía `httpx` (el flujo confirmado como real en el legacy; nunca se usó `authlib`). 6 tests con `httpx.AsyncClient` mockeado. Rutas `GET /api/auth/google` (redirige a Google) y `GET /api/auth/google/callback` (intercambia code, redirige a `{FRONTEND_URL}/auth/google-callback?token=...`).
- **Fix de higiene**: `python-jose`, `bcrypt`, `email-validator` (usados desde los incrementos 1-2) nunca habían quedado declarados en `requirements.txt` — estaban instalados globalmente pero no pedidos por el proyecto. Se corrigió junto con `httpx` (nuevo, usado por este incremento).

### Credenciales reales (decisión del desarrollador)

Se reutiliza el mismo `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` que ya usa el legacy
(`inventarios/.env`), agregados al `.env` del proyecto nuevo con
`GOOGLE_REDIRECT_URI=http://localhost:3040/api/auth/google/callback` (puerto nuevo del
backend). **Pendiente en Google Cloud Console** (fuera del alcance de esta sesión): agregar
`http://localhost:3040/api/auth/google/callback` a los "Authorized redirect URIs" de ese
Client ID — sin eso, Google devuelve `redirect_uri_mismatch` al intercambiar el `code` real.
El frontend (`localhost:3000`) mantiene la misma ruta `/auth/google-callback` esperando el
token por query param, confirmado por el desarrollador — sin cambios respecto al legacy.

### Verificación

- `GET /api/auth/google` probado con `TestClient` real: redirige (307) a la URL de Google
  correcta, con `client_id`/`redirect_uri` tomados de `.env`.
- `GET /api/auth/google` sin credenciales: 500 con `AUTH-011` (`GoogleOAuthNoConfiguradoError`), verificado end-to-end.
- El flujo completo del callback (intercambio de `code` real) **no se pudo probar
  end-to-end** en esta sesión porque requiere una interacción real de un usuario con la
  pantalla de consentimiento de Google — cubierto en cambio con 6 tests del adaptador
  (`httpx` mockeado: éxito, error de intercambio, email faltante, credenciales faltantes)
  y 6 tests del servicio (creación, vínculo, cuenta ya vinculada, colisión de username, usuario inactivo).
- Suite completa: 57/57 tests verdes.

### Checklist del incremento 3

- [x] Domain — 2 métodos de transición + 2 errores nuevos
- [x] Application — `GoogleOAuthPort`, DTO, ampliación de `UsuarioRepositoryPort`, 2 servicios, 8 tests
- [x] Infrastructure — `GoogleOAuthAdapter`, 6 tests, 2 rutas nuevas
- [x] `requirements.txt` corregido (gap de incrementos previos + `httpx` nuevo)
- [x] Verificación real de `/google` (éxito y error de configuración); callback verificado solo con mocks (requiere interacción real con Google)
- [ ] **Pendiente del desarrollador**: agregar el redirect URI del puerto 3040 en Google Cloud Console para poder probar el callback completo con un usuario real

## Incremento 4 — Gestión admin de usuarios (completo) — **módulo `auth` cerrado**

Rutas bajo `/api/auth/usuarios` (mismo router que el resto de `auth`, no un prefijo
`/api/admin` separado, por decisión del desarrollador), todas protegidas con
`require_super_admin` (ya existía desde el incremento 1).

- **Domain**: `Usuario.crear_por_admin(email, username, password_hash, rol, creado_por)` — a diferencia de `crear()`/`crear_desde_google()`, acá `creado_por` ya viene resuelto (el admin autenticado tiene un id real, no hay que esperar a que Mongo genere uno). `Usuario.actualizar_admin(actualizado_por, username?, rol?, activo?, password_hash?)` para updates parciales. Errores nuevos: `UsuarioAdminNoEncontradoError` (404 — distinto de `UsuarioNoEncontradoError`, que es 401 y es específico del flujo JWT; se creó uno nuevo en vez de reutilizar el existente al notar que compartir la clase habría dado una semántica HTTP incorrecta) y `OperacionSobrePropioUsuarioNoPermitidaError` (400, mismo status que el legacy, para bloquear que un super_admin se edite/elimine a sí mismo).
- **Application**: `UsuarioRepositoryPort` ampliado con `listar_paginado` (reutilizando `RespuestaPaginada`, en vez del listado sin paginar del legacy) y `eliminar`. Servicios: `ListarUsuariosService`, `CrearUsuarioAdminService` (acepta `rol` explícito, a diferencia del registro público), `ActualizarUsuarioAdminService`, `EliminarUsuarioAdminService`. 13 tests nuevos.
- **Infrastructure**: `UsuarioPipelineBuilder` (mismo patrón que `TareaPipelineBuilder`). Rutas `GET/POST /api/auth/usuarios`, `PUT/DELETE /api/auth/usuarios/{id}`.

### Bug real encontrado y corregido: `crear()` pisaba el `creado_por` real en creación por admin

Al extender `MongoUsuarioRepository` se detectó que `crear()` **siempre** sobreescribía
`creado_por.id_persona` con el id del usuario recién insertado — correcto para
auto-registro/Google (donde el creador es el propio usuario nuevo, ver incremento 1), pero
**incorrecto** para creación por admin (donde `creado_por` ya es el id real del admin
autenticado y no debía tocarse). Se corrigió condicionando el patch solo al caso de
`id_persona` vacío (el placeholder usado en auto-registro/Google), con 2 tests de regresión
específicos para no repetir el bug.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Usuario de prueba promovido a `super_admin` directamente en Mongo (no hay forma de crear un
super_admin por API pública, por diseño): login → listar usuarios paginado → crear usuario
con rol `admin` explícito → actualizar (desactivar) → intentar actualizarse a sí mismo (400,
`AUTH-013`) → intentar eliminarse a sí mismo (400, `AUTH-013`) → eliminar el usuario creado
(200) → eliminarlo de nuevo (404, `AUTH-012`, confirmando la categoría `NOT_FOUND` correcta).
Los 9 casos se comportaron como se diseñó. `users` (legacy) verificada intacta con sus 3
documentos originales antes y después. Suite completa: **72/72 tests verdes**.

### Checklist del incremento 4

- [x] Domain — 2 métodos de transición + 2 errores nuevos
- [x] Application — ampliación de `UsuarioRepositoryPort`, 4 servicios, 13 tests
- [x] Infrastructure — `UsuarioPipelineBuilder`, bugfix en `crear()` + 2 tests de regresión, 4 rutas nuevas
- [x] Verificación end-to-end completa (9 casos) contra `inventario_db` real, con limpieza de datos de prueba

---

## Módulo `auth` — CERRADO (4/4 incrementos completos)

Los 4 incrementos acordados en la Fase 0 original quedaron completos: login/registro/roles,
recuperación de password, Google OAuth, gestión admin de usuarios. 72 tests unitarios,
verificación end-to-end de cada incremento contra la base real (`inventario_db`, colección
aislada `usuarios`), sin ningún impacto sobre la colección `users` del legacy en ningún
momento. `shared/infrastructure/api/dependencies/auth.py` (`get_current_usuario`,
`require_authenticated`, `require_super_admin`, `require_admin_or_super`) queda disponible
para que el resto de los módulos del plan (`productos`, `ubicaciones`, etc.) lo usen sin
ninguna dependencia adicional.

**Siguiente módulo según la prioridad de migración**: `productos`.

## Observaciones

Módulo fundacional: ningún otro módulo debe empezar su Fase 3 (Construcción) hasta que
`auth` tenga al menos `LoginService` y la dependencia HTTP de "usuario actual" disponible,
porque todos los demás routers dependen de `require_authenticated` / `require_super_admin`.
**Esta condición ya se cumple** — ambos existen desde este incremento.

### Hallazgo durante la construcción: `scripts/mongo/sync_schema` no existía

El template documentaba (`.claude/MONGODB.md`, `docs/mongo/gestion_de_schemas.md`) un
comando `scripts.mongo.sync_schema` que en realidad no estaba implementado en este
repositorio (tampoco `shared/infrastructure/persistence/mongo/schema/runner.py`). Se
construyó como parte de esta sesión, ya que es infraestructura compartida que **todos**
los módulos futuros necesitan para sincronizar sus colecciones, no algo específico de `auth`:

- `shared/infrastructure/persistence/mongo/schema/runner.py` — motor de sincronización (crea colecciones/aplica `collMod`, compara índices declarados vs. existentes, soporta `--dry-run` y `--drop-extra-indexes`, nunca toca el índice `_id_`).
- `scripts/mongo/sync_schema.py` — CLI (`python -m scripts.mongo.sync_schema [--dry-run] [--only col1 col2] [--drop-extra-indexes]`).
- 13 tests unitarios en `tests/unit/shared/infrastructure/persistence/mongo/schema/test_runner.py`.
- Verificado con un `--dry-run` real contra una instancia de MongoDB alcanzable en el entorno de desarrollo.

### Hallazgo crítico: colisión con la colección `users` real del legacy

El primer `--dry-run` se corrió apuntando por error a `inventario_db` (la base real del
sistema legacy, cuya URL vive en `inventarios/.env`, en el mismo servidor Mongo
`localhost:27017`). Se detectó que **`inventario_db.users` ya existe con 3 documentos
reales** (probablemente las cuentas semilla `superadmin@fimlm.org`, `admin@fimlm.org`,
`operativo@fimlm.org`), con esta forma:

```
_id, created_at, email, email_verified, google_id, google_picture, is_active, password_hash, rol, username
```

Esto **no es compatible** con la entidad `Usuario` nueva: los nombres de campo difieren
(`is_active` vs `activo`, `created_at` vs `creado_por`, `email_verified` vs
`email_verificado`) y **no existe `creado_por`**, campo obligatorio en el schema nuevo.
Aplicar el validator nuevo sobre la colección `users` existente habría sido riesgoso
(actualizaciones futuras a esos 3 documentos habrían sido rechazadas por Mongo), y aunque
el validator no fuera un problema, **el código de lectura (`MongoUsuarioRepository`)
habría lanzado una excepción no controlada (500)** al intentar construir un `Usuario` a
partir de esos documentos, porque `creado_por` es obligatorio y no está presente.

**Decisión tomada con el desarrollador:** el módulo `auth` usa una colección separada,
**`usuarios`** (no `users`), en la misma base `inventario_db`. Cero colisión con los datos
del legacy, cero necesidad de migrar esos 3 usuarios ahora (queda pendiente como una
migración de datos aparte, si se decide hacerla en el futuro). Se renombraron:

- Archivo: `usuarios_collection.py` (antes `users_collection.py`), constante `USUARIOS_COLLECTION`.
- Colección Mongo: `usuarios` (antes `users`).
- Índices: `uq_usuarios_email`, `uq_usuarios_username`, `idx_usuarios_google_id`, `idx_usuarios_reset_token`, `idx_usuarios_creado_fecha`.
- `MongoUsuarioRepository.COLECCION = "usuarios"`.

Verificado con `--dry-run --only usuarios` contra `inventario_db` real: planeaba crear
`usuarios` (nueva, vacía) con sus 5 índices, sin tocar `users` (legacy) ni ninguna otra
colección. **Aplicado luego para real** (`sync_schema --only usuarios`, sin `--dry-run`):
la colección `usuarios` quedó creada (0 documentos, 6 índices incluyendo `_id_`).
Confirmado por lectura directa que `users` (legacy) sigue con sus 3 documentos intactos
y sin ningún cambio.

Pendiente: el proyecto nuevo todavía no tiene `.env` en su raíz — se usaron variables de
entorno inline (`MONGO_URL`, `MONGO_DB=inventario_db`, `JWT_SECRET_KEY`) solo para esta
verificación puntual, no persistidas en disco. El desarrollador debe crear su propio
`.env` local (fuera de git) antes de levantar la app de forma normal con `python main.py`.

### Hallazgo crítico (durante el análisis de Fase 0 de `ubicaciones`): `MongoUnitOfWork` no funcionaba contra el servidor real — resuelto

Al analizar el módulo `ubicaciones` (el de mayor riesgo de consistencia de todo el plan, ver
esa sección) se encontraron tres problemas reales, verificados contra el código legacy y contra
Mongo:

1. **Bug activo en producción**: `crud.py::crear_movimiento_ubicacion` (legacy) referencia una
   variable `movimiento` que no existe en ningún lado del módulo — `NameError` garantizado.
   Como se llama *después* de insertar el documento de ubicación, el efecto real es: la
   ubicación se crea en Mongo, pero el request siempre responde 500. No se corrigió (es código
   legacy, fuera de alcance hasta que se migre esa responsabilidad) — solo se documenta.
2. **Datos reales ya corruptos**: varios de los 12 documentos de `inventario_db.ubicaciones`
   tienen `stock_fisico`/`stock_reservado` **negativos** (ej. `-27`, `-77`, `-223`) — confirma
   que el riesgo de consistencia que ya anotaba este plan no es teórico. Sin corregir todavía;
   es una tarea de datos aparte, a decidir cuándo abordarla.
3. **`MongoUnitOfWork` (`shared/infrastructure/persistence/mongo/unit_of_work.py`) usa
   transacciones reales de Mongo, que requieren un replica set** — el servidor real
   (`localhost:27017`, compartido con el legacy) era un **standalone** (`replSetGetStatus` →
   `NoReplicationEnabled`). La clase nunca se había usado ni probado en ningún lado del código.
   Esto invalidaba la estrategia de consistencia que el plan daba por hecha para `ubicaciones`.

**Resuelto con el desarrollador**: se convirtió el `mongod` local a un **replica set de un
solo nodo** (`rs0`) — se agregó `replication.replSetName: rs0` a
`C:\Program Files\MongoDB\Server\8.2\bin\mongod.cfg` y se reinició el servicio de Windows
`MongoDB` (pasos ejecutados por el desarrollador, ya que requieren permisos de administrador).
MongoDB 8.2 auto-inicializó el replica set de un solo nodo al arrancar sin estado previo —
quedó como `PRIMARY` sin necesidad de un `rs.initiate()` manual.

Verificado tras la conversión:
- Todas las colecciones y conteos de documentos intactos (`productos`: 6, `users`: 3,
  `ubicaciones`: 12, sin cambios) — el reinicio del servicio no tocó ningún dato.
- `MongoUnitOfWork` probado end-to-end contra una colección temporal: commit persiste los
  documentos de la transacción, y una excepción a mitad de camino hace rollback automático del
  insert parcial (confirmado, luego se limpió la colección de prueba).
- Suite completa del proyecto nuevo: 93/93 tests verdes, sin regresiones por el reinicio.

Con esto, `MongoUnitOfWork` queda disponible y validado para `ubicaciones` (y cualquier módulo
futuro que necesite transacciones multi-colección), tal como el plan ya asumía — la asunción
ahora es cierta, no solo aspiracional.

---

# Módulo `productos`

## Objetivo

Mantener el catálogo maestro de productos: alta, edición, baja, búsqueda, códigos
identificadores (código interno, código de barras, QR), imagen asociada (solo categoría
`SOUVENIR` en el legacy) y carga/descarga masiva vía Excel/CSV.

## Fase 0 — Alcance acordado (WORKFLOW.md)

Decisiones cerradas con el desarrollador antes de pasar a Fase 1 (modelado Mongo):

| Pregunta | Decisión |
|---|---|
| Alcance del **primer incremento** de construcción | Solo CRUD básico: `CrearProductoService`, `ActualizarProductoService`, `EliminarProductoService`, `ObtenerProductoService`, `ListarProductosService`, `BuscarProductosService`. Carga masiva Excel, código de barras/QR y gestión de imagen quedan diseñados en este documento pero se construyen en incrementos posteriores del mismo módulo — no en esta primera pasada (mismo patrón que `auth`). |
| Identificador público de producto en las rutas | **`codigo`** (no ObjectId). Resuelve la ambigüedad confirmada en el legacy: la mayoría de endpoints de `crud.py` aceptaban indistintamente código u ObjectId con fallback, pero `subir_imagen_producto` (`routers/productos.py:818`) usaba `ObjectId(producto_id)` directo sin fallback, rompiendo con un código. El `_id` de Mongo queda como detalle interno de persistencia. |
| Autenticación en endpoints de escritura | **Todos los endpoints de escritura** (crear/actualizar/eliminar) requieren `require_authenticated` (ya disponible desde `shared/infrastructure/api/dependencies/auth.py`, construido en el módulo `auth`). Difiere del legacy, donde estaban comentados/deshabilitados en varios endpoints (`#current_user: dict = Depends(require_authenticated)`). Endpoints de solo lectura (listar, obtener, buscar) quedan sin autenticación en este incremento. |
| `precio_unitario` en la creación | Se **corrige** un bug real del legacy: `crud.py::crear_producto` (líneas 82-92) arma el documento a insertar sin incluir `precio_unitario` en absoluto, aunque el modelo `ProductoCreate` sí lo declara — hoy solo se puede fijar el precio vía carga Excel o edición posterior, nunca en el alta normal. `CrearProductoDTO` nuevo acepta `precio_unitario` opcional (`>= 0`, default `0.0`) desde el primer incremento. |

### Hallazgos confirmados contra el código legacy (no solo el resumen del plan)

- **`schemas.py::ProductoBase`/`ProductoUpdate` — código muerto confirmado.** Están duplicadas (línea 41 y línea 202, la segunda sombrea a la primera), pero ninguna de las dos se usa: `routers/productos.py` importa `ProductoCreate`/`ProductoUpdate` desde `models.py`, no desde `schemas.py`. Mismo patrón que `UserLogin`/`UserRegister` en el módulo `auth`. El contrato HTTP real y vigente es `models.py::ProductoCreate/ProductoUpdate`, que sí incluye `precio_unitario`.
- **Ambigüedad de identificador — confirmada** (ver decisión de tabla arriba: `subir_imagen_producto` no tiene el fallback código→ObjectId que sí tienen `get_producto`/`actualizar_producto`/`eliminar_producto`).
- **`precio_unitario` — confirmado que sigue vigente en el dominio real**: se usa en `crud.py::get_valor_total_inventario` (línea 554, `$multiply: stock_actual * precio_unitario`) para el reporte de valor total de inventario (`inventario_reportes`). El bug de que no se persiste en la creación (ver tabla arriba) es un hallazgo nuevo, no documentado en la versión anterior de este plan.

Con esto, el **checklist de Fase 0** de `.claude/WORKFLOW.md` queda completo para el primer incremento de este módulo. Sigue la Fase 1 (modelado de la colección `productos` en Mongo) antes de escribir cualquier código.

## Fase 1 — Modelado MongoDB (colección `catalogo_productos`) — **APROBADA**

### Hallazgo crítico: colisión con la colección `productos` real del legacy

Verificado en modo solo lectura contra `inventario_db` (mismo servidor que usa `auth`): la
colección `productos` **ya existe con 6 documentos reales de producción** (ARROZ, ACEITE,
LENTEJA y 3 más), con stock real (ej. 6103, 5115 unidades) y esta forma:

```
_id, codigo, nombre, descripcion, categoria, stock_minimo, stock_actual, imagen_url,
fecha_creacion, fecha_actualizacion
```

Índices existentes: único en `codigo`, texto en `nombre`, `categoria`, `stock_actual`,
`fecha_creacion` descendente — coinciden con lo que ya proponía este plan.

A diferencia del caso `users`/`usuarios` (donde los nombres de campo diferían bastante), acá
la forma es casi idéntica a la propuesta — el único problema real es que **ninguno de los 6
documentos tiene `creado_por`** (obligatorio en el patrón de auditoría nuevo), y se confirmó
además que **ninguno tiene `precio_unitario` seteado** (consistente con el bug de creación ya
documentado en Fase 0). Uno de los 6 (código `800`) sí tiene `imagen_url` cargada.

**Decisión tomada con el desarrollador:** mismo criterio que en `auth` — colección aislada,
**`catalogo_productos`** (no `productos`), en la misma base `inventario_db`. Cero colisión con
los 6 productos reales del legacy; su migración a la colección nueva queda pendiente como
tarea de datos aparte, si se decide hacerla en el futuro. Los módulos `ubicaciones`/
`movimientos` que dependen de `productos` deberán apuntar a `catalogo_productos` cuando se
construyan.

### Inconsistencia resuelta: `fecha_creacion`/`fecha_actualizacion` vs. `AuditPersona`

La entidad `Producto` descrita más abajo en este documento (sección Domain, escrita antes de
que se cerrara el patrón `AuditPersona` durante la construcción de `auth`) listaba
`fecha_creacion`/`fecha_actualizacion` como campos propios. `.claude/MONGODB_MODELING.md`
establece que **siempre** se usa `creado_por`/`actualizado_por` en lugar de
`created_at`/`updated_at` sueltos — regla ya aplicada en `usuarios` (sin campos de fecha
aparte, la fecha vive en `creado_por.fecha`/`actualizado_por.fecha`). Se resuelve aplicando la
misma regla acá: no hay `fecha_creacion`/`fecha_actualizacion` como campos independientes en
`catalogo_productos`.

### Estructura del documento

| Campo | Tipo (bsonType) | Obligatorio | Notas |
|---|---|---|---|
| `_id` | objectId | sí | id técnico |
| `codigo` | string | sí | identificador público único (provisto o autogenerado `PROD-YYYYMMDD-XXXXXX`) |
| `nombre` | string | sí | 1–200 caracteres validado en domain/DTO, no en el validator de Mongo |
| `descripcion` | string\|null | no | |
| `categoria` | string\|null | no | libre, sin enum (igual que el legacy) |
| `stock_minimo` | int | sí | default 0 |
| `stock_actual` | int | sí | default 0; denormalizado — este incremento no lo expone como editable directo, se recalculará desde `ubicaciones`/`movimientos` en módulos futuros |
| `precio_unitario` | double | sí | default 0.0 (decisión Fase 0: se corrige el bug legacy, se acepta desde la creación) |
| `imagen_url` | string\|null | no | incremento futuro (subir/eliminar imagen); se modela desde ya sin código que lo use todavía, mismo patrón que los campos de Google OAuth en `auth` |
| `creado_por` | object (`AuditPersona`) | sí | |
| `actualizado_por` | object (`AuditPersona`) | no | nulo hasta la primera actualización |

Embeber vs referenciar: colección raíz, sin subdocumentos — no aplica todavía (este incremento
no toca `ubicaciones`). Historial de estados: no aplica (producto no tiene flags de estado).

### Índices propuestos

| Nombre | Campos | Tipo | Responde a |
|---|---|---|---|
| `uq_catalogo_productos_codigo` | `codigo` (1) | único | identificador público, evita duplicados |
| `idx_catalogo_productos_nombre_texto` | `nombre` (text, es) | texto | `BuscarProductosService` |
| `idx_catalogo_productos_categoria` | `categoria` (1) | normal | filtrar por categoría |
| `idx_catalogo_productos_stock_actual` | `stock_actual` (1) | normal | productos bajo stock (reportes futuros) |
| `idx_catalogo_productos_creado_fecha` | `creado_por.fecha` (-1) | normal | listado administrativo por antigüedad |

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/routers/productos.py` (endpoints de producto, no los de ubicación — ver módulo `ubicaciones`) | Rutas CRUD, búsqueda, carga Excel, plantilla Excel, código de barras/QR, subir/eliminar imagen | `infrastructure/api/routes.py` |
| `app/crud.py::get_producto, get_producto_por_codigo, get_productos, crear_producto, actualizar_producto, contar_productos, eliminar_producto, buscar_productos` | Persistencia de productos | `application/services/*` + `infrastructure/persistence/mongo/producto_repository.py` |
| `app/models.py::Producto, ProductoCreate, ProductoUpdate` | Entidad y DTOs de producto | `domain/entities/producto.py` + `application/dto/` |
| `app/schemas.py::ProductoBase/ProductoCreate/ProductoUpdate/Producto` (ambas definiciones duplicadas, ver Riesgos) | Schemas HTTP | `infrastructure/api/schemas.py` |
| `app/utils/codigos.py` | Generación de código interno, código de barras (Code128) y QR en base64 | `infrastructure/codigos/` (adaptador específico del módulo, no genérico) |
| Sección de `crud.py` sobre carga Excel (dentro del router, no en `crud.py`: la lógica vive inline en `routers/productos.py::cargar_productos_excel`) | Importación masiva desde Excel/CSV con `pandas`/`chardet` | `application/services/cargar_productos_masivo.py` + adaptador de parsing en `infrastructure/` |
| Subida de imagen (`routers/productos.py::subir_imagen_producto/eliminar_imagen_producto`) | Guardar/eliminar archivo de imagen en disco | `application/services/` usando `StorageRepositoryPort` (candidato shared) |

## Responsabilidades detectadas

- CRUD de producto (código, nombre, descripción, categoría, stock mínimo, precio unitario, imagen).
- Generación automática de código si no se especifica (`PROD-YYYYMMDD-XXXXXX`).
- Búsqueda por nombre/código/descripción (regex case-insensitive).
- Generación de código de barras y QR bajo demanda (no se persisten, se generan al vuelo).
- Carga masiva desde Excel/CSV con validación de duplicados (en archivo y en BD).
- Descarga de plantilla Excel de ejemplo.
- Subida/eliminación de imagen, restringida a categoría `SOUVENIR`.

## Domain

- **Entities**: `Producto` (codigo, nombre, descripcion, categoria, stock_minimo, stock_actual, precio_unitario, imagen_url, fecha_creacion, fecha_actualizacion). `stock_actual` es un campo **denormalizado** que se recalcula desde `ubicaciones` — su consistencia es responsabilidad del módulo `movimientos`/`ubicaciones`, no de `productos`.
- **Errors**: código duplicado, producto no encontrado, categoría no permite imagen, archivo/formato inválido en carga masiva, columnas obligatorias faltantes.

## Application

- **DTO**: `CrearProductoDTO`, `ActualizarProductoDTO`, `ProductoDTO` (salida), `ResultadoCargaMasivaDTO`.
- **Ports**: `ProductoRepositoryPort` (buscar por id/código, listar paginado, buscar por texto, crear, actualizar, eliminar, contar), `StorageRepositoryPort` (guardar/eliminar imagen), `GeneradorCodigoPort` (código de barras/QR).
- **Services**: `CrearProductoService`, `ActualizarProductoService`, `EliminarProductoService`, `ObtenerProductoService`, `ListarProductosService`, `BuscarProductosService`, `CargarProductosMasivoService`, `GenerarCodigoBarrasService`, `GenerarQrProductoService`, `SubirImagenProductoService`, `EliminarImagenProductoService`.

## Infrastructure

- **Persistence**: `MongoProductoRepository` (colección `productos`), índices: único en `codigo`, texto en `nombre`, por `categoria`, por `stock_actual`, por `fecha_creacion` (todos ya existían en el legacy `database.py::create_indexes` — deben re-declararse como `MongoCollectionDefinition`).
- **API**: rutas `/api/productos` (CRUD, búsqueda), `/api/productos/plantilla-excel`, `/api/productos/cargar-excel`, `/api/productos/{id}/codigo-barras`, `/api/productos/{id}/qr-code`, `/api/productos/{id}/subir-imagen`, `/api/productos/{id}/eliminar-imagen`.
- **Codigos**: adaptador con `python-barcode` + `qrcode` + `Pillow` (dependencias externas ya usadas en legacy).

## Bootstrap

`register_module(app)` registra el router de productos.

## Validaciones

- `nombre`: 1–200 caracteres, obligatorio.
- `stock_minimo`, `precio_unitario`: `>= 0`.
- `codigo`: único; si no se provee, se autogenera.
- Imagen: solo para `categoria == "SOUVENIR"`, solo `content_type` de imagen.
- Excel: columnas `codigo` y `nombre` obligatorias; códigos no duplicados ni en el archivo ni en BD.

## Riesgos

- ~~Duplicación de clases: `app/schemas.py` define `ProductoBase` y `ProductoUpdate` dos veces...~~ **RESUELTO (verificado en código, Fase 0):** ninguna de las dos definiciones se usa — `routers/productos.py` importa `ProductoCreate`/`ProductoUpdate` desde `models.py`, no desde `schemas.py`. Código muerto, mismo patrón que `UserLogin`/`UserRegister` en `auth`. El contrato real es `models.py::ProductoCreate/ProductoUpdate`, que sí incluye `precio_unitario`.
- El campo `id: int` en `schemas.py::Producto` es un remanente de un diseño SQL anterior; el proyecto real usa `ObjectId`/`codigo` como identificador string. Es código muerto/inconsistente — no migrar tal cual.
- ~~La subida de imagen busca el producto por `_id` (ObjectId) directamente...~~ **RESUELTO (decisión Fase 0):** identificador público único = `codigo` para todas las rutas de este módulo (ver tabla de Fase 0).
- **Nuevo hallazgo (Fase 0):** `crud.py::crear_producto` nunca persiste `precio_unitario` al crear, aunque el campo existe en `ProductoCreate` — solo se fija vía carga Excel o edición posterior. Decisión Fase 0: se corrige en el diseño nuevo (ver tabla de Fase 0).

## Utilidades reutilizables

- Ninguna se comparte con otros módulos de negocio. `codigos.py` es específico de la identidad de producto.

## Refactorizaciones recomendadas

- ~~Unificar el identificador de producto en las rutas...~~ **RESUELTO (decisión Fase 0):** `codigo` en todas las rutas.
- ~~Decidir si `precio_unitario` sigue siendo parte del dominio...~~ **RESUELTO (decisión Fase 0):** sí, y se corrige el bug de creación (ver Fase 0).
- **Pendiente para cuando se implemente `BuscarProductosService` con más volumen de datos:** la búsqueda actual usa `$regex` sobre `nombre`/`codigo`/`descripcion` (igual que el legacy, con `re.escape()` agregado por seguridad), que **no** usa el índice de texto `idx_catalogo_productos_nombre_texto` (los índices de texto solo aceleran queries `$text`). Es el mismo estado que el legacy, no una regresión — pero si el catálogo crece, migrar la búsqueda a `$text` (con la contrapartida de perder el match por código/descripción, o combinar ambas estrategias).
- **Hallazgo de infraestructura compartida:** `MongoIndexDefinition` (`shared/infrastructure/persistence/mongo/schema/definitions.py`) no soporta `default_language` — el índice de texto de `catalogo_productos` quedó creado con idioma `english` (default de Mongo) en vez de `spanish` como tenía el índice del legacy. No afecta a este incremento (no se usa `$text` todavía), pero queda pendiente si algún incremento futuro sí lo necesita.

## Código que NO debe migrarse

- La clase `Producto`/`ProductoBase`/`ProductoUpdate` de `schemas.py` con `id: int` (remanente SQL).
- Comentarios de código muerto (`#precio_unitario...`, `#ubicacion...`) dentro de `ProductoBase`.

## Checklist de migración

- [x] Domain — `Producto` (`crear`/`actualizar`), errores `PROD-001`/`PROD-002`
- [x] Application — DTOs, `ProductoRepositoryPort`, 6 servicios (CRUD básico + listar + buscar), 14 tests
- [x] Infrastructure — `MongoProductoRepository`, schema Mongo `catalogo_productos` registrado y sincronizado
- [x] API — `GET/POST /api/productos`, `GET /api/productos/buscar`, `GET/PUT/DELETE /api/productos/{codigo}`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 21 tests unitarios + verificación end-to-end (22 casos) contra `inventario_db` real

**Pendiente para incrementos posteriores del mismo módulo** (fuera del alcance de este incremento, según Fase 0): carga masiva Excel, código de barras/QR, subida/eliminación de imagen.

## Incremento 1 — CRUD básico (completo)

- **Domain**: `Producto.crear()` (código ya resuelto por el service) y `Producto.actualizar()` (update parcial inmutable, `model_copy`). Sin errores de validación de dominio propios: `nombre`/`stock_minimo`/`precio_unitario` se validan con `Field` de Pydantic en los DTOs (mismo criterio que `auth`). 2 errores nuevos: `ProductoCodigoDuplicadoError` (`PROD-001`, 409), `ProductoNoEncontradoError` (`PROD-002`, 404).
- **Application**: `CrearProductoInput`/`ActualizarProductoInput`/`ListarProductosInput`, `ProductoRepositoryPort` (7 métodos, todo por `codigo`, sin `obtener_por_id` — no hace falta con el identificador único decidido en Fase 0), 6 servicios. Decisión de diseño: los servicios reciben `AuditPersona` ya construida (no el `Usuario` autenticado) para que `application/` de `productos` no importe nada de `modules.auth` — la traducción `Usuario → AuditPersona` vive en `infrastructure/api/routes.py`. `CrearProductoService` autogenera código (`PROD-YYYYMMDD-XXXXXX` con `secrets.token_hex`, más seguro que el `random.choices` del legacy) y aplica la misma validación de unicidad tanto al código provisto como al autogenerado. 14 tests.
- **Infrastructure**: `MongoProductoRepository` (colección `catalogo_productos`), `ProductoPipelineBuilder` (paginado, mismo patrón que `UsuarioPipelineBuilder`). Corrección de seguridad en `buscar_por_texto`: el legacy pasaba el término de búsqueda directo a `$regex` sin escapar (inyección de metacaracteres regex, riesgo de ReDoS) — se agregó `re.escape()`, con 2 tests de regresión (detectado en la revisión de `.claude/SOLID_CHECKLIST.md`, que exige prueba para todo bug corregido). Rutas `GET/POST /api/productos`, `GET /api/productos/buscar`, `GET/PUT/DELETE /api/productos/{codigo}`, las 3 de escritura protegidas con `require_authenticated`.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Se probó el flujo completo con un usuario y un producto de prueba reales (creados y luego
eliminados): registro de usuario → login → crear producto sin auth (401) → crear producto con
`precio_unitario` (201, verificado que se persiste desde la creación) → crear duplicado (409)
→ obtener por código (200) → obtener inexistente (404) → buscar por texto (encuentra el
producto) → buscar con metacarácter de regex `(.*)` (200, no rompe y no matchea de más,
confirma que `re.escape()` funciona) → listar paginado (incluye el producto) → actualizar sin
auth (401) → actualizar parcial (200, solo cambia el campo enviado) → actualizar inexistente
(404) → eliminar sin auth (401) → eliminar (200) → eliminar de nuevo (404) → obtener tras
eliminar (404). Los 22 casos se comportaron como se diseñó. `productos` (legacy) verificada
intacta con sus 6 documentos originales antes y después; `catalogo_productos` quedó vacía
(0 documentos) tras la limpieza. Suite completa: **93/93 tests verdes**.

### Checklist del incremento 1

- [x] Domain — `Producto` + 2 errores nuevos, 5 tests
- [x] Application — DTOs, puerto, 6 servicios, 14 tests
- [x] Infrastructure — `MongoProductoRepository`, schema `catalogo_productos` sincronizado (5 índices), corrección de seguridad en búsqueda por texto + 2 tests de regresión
- [x] Verificación end-to-end completa (22 casos) contra `inventario_db` real, con limpieza de datos de prueba

## Observaciones

Depende de `auth` solo para la dependencia HTTP `require_authenticated` (vía `shared/`), no
para lógica de dominio — `application/` de `productos` no importa nada de `modules.auth`
(ver Incremento 1). El legacy tenía `require_authenticated`/`require_super_admin`
**comentados** en varios endpoints (`#current_user: dict = Depends(require_authenticated)`).
**Resuelto en Fase 0:** todos los endpoints de escritura del incremento 1 requieren
`require_authenticated`.

**Siguiente módulo según la prioridad de migración**: `ubicaciones` (depende de `productos`,
ya disponible desde este incremento).

---

# Módulo `ubicaciones`

## Objetivo

Registrar y mantener el stock físico de cada producto distribuido por ubicación (bodega/anaquel/etc.), permitiendo crear, actualizar, eliminar y transferir stock entre ubicaciones, manteniendo la suma de ubicaciones consistente con `productos.stock_actual`.

## Fase 0 — Alcance acordado (WORKFLOW.md)

Decisiones cerradas con el desarrollador antes de pasar a Fase 1 (modelado Mongo):

| Pregunta | Decisión |
|---|---|
| Dependencias faltantes (`movimientos`, `reservas`, ninguno de los dos módulos existe todavía) | **Se omiten ambas responsabilidades en este incremento** (recomendado): no se registra movimiento al crear/transferir ubicación, y el stock disponible no cruza contra `reservas` (solo resta `stock_reservado` propio del documento). Deuda explícita documentada, a resolver cuando existan esos módulos — sin puertos "no-op" prematuros. |
| Alcance del **primer incremento** de construcción | **CRUD + transferencia completos**: `CrearUbicacionService`, `ActualizarUbicacionService`, `EliminarUbicacionService`, `ObtenerProductoConUbicacionesService`, `TransferirStockService` — todo en un solo incremento, usando `MongoUnitOfWork` (ya validado contra el replica set real, ver hallazgo al cierre de `auth`) para las operaciones que tocan `ubicaciones` + `productos.stock_actual` a la vez. |
| Estrategia de sincronización `productos.stock_actual` | **Recalcular desde cero en cada mutación**: tras crear/actualizar/eliminar/transferir una ubicación, se vuelve a sumar `stock_fisico` de TODAS las ubicaciones del producto y se escribe ese total. Autocorrige drift previo; evita la clase de bug que ya produjo los valores negativos reales encontrados en `inventario_db.ubicaciones` (delta incremental `$inc`, patrón del legacy, descartado). |
| Prefijo de rutas HTTP | **Anidado bajo productos**: `/api/productos/{codigo}/ubicaciones/...` — una ubicación siempre pertenece a un producto, mismo criterio que el legacy. El identificador público de una ubicación es el par `(codigo_producto, ubicacion)`, sin ObjectId expuesto (mismo criterio que la decisión de identificador de `productos`). |
| Autenticación en endpoints de escritura | **Todos los endpoints de escritura** (crear, actualizar, eliminar, transferir) requieren `require_authenticated`. Lectura (obtener producto con ubicaciones) queda sin autenticación. Difiere del legacy, que tenía la protección comentada en `crear_ubicacion_producto`/`transferir_stock`. |

Con esto, el **checklist de Fase 0** de `.claude/WORKFLOW.md` queda completo para el primer incremento de este módulo. Sigue la Fase 1 (modelado de la colección `ubicaciones` en Mongo) antes de escribir cualquier código — la verificación de solo lectura contra `inventario_db.ubicaciones` (12 documentos reales, sin índices más allá de `_id_`, varios con `stock_fisico`/`stock_reservado` negativos) ya se hizo como parte del análisis de esta Fase 0 (ver hallazgo al cierre de `auth`).

## Fase 1 — Modelado MongoDB (colección `stock_ubicaciones`) — **APROBADA**

### Colisión con `ubicaciones` real del legacy

Mismo criterio que `auth` (`users`→`usuarios`) y `productos` (`productos`→`catalogo_productos`):
**colección aislada, `stock_ubicaciones`**, en la misma base `inventario_db`. Cero colisión con
los 12 documentos reales del legacy (varios con `stock_fisico`/`stock_reservado` negativos, sin
`creado_por`) — su limpieza/migración queda pendiente como tarea de datos aparte.

### Estructura del documento

| Campo | Tipo (bsonType) | Obligatorio | Notas |
|---|---|---|---|
| `_id` | objectId | sí | id técnico |
| `producto_codigo` | string | sí | referencia por convención a `catalogo_productos.codigo` (sin `$ref`, mismo criterio que el legacy) |
| `ubicacion` | string | sí | nombre de la ubicación física (ej. `"A10-1"`); único junto con `producto_codigo` |
| `stock_fisico` | int | sí | `>= 0` validado en domain/DTO, no en Mongo |
| `stock_reservado` | int | sí | default 0; incremento futuro (módulo `reservas`) — sin servicio que lo mute todavía en este incremento, mismo patrón que `imagen_url` en `productos` |
| `creado_por` | object (`AuditPersona`) | sí | |
| `actualizado_por` | object (`AuditPersona`) | no | nulo hasta la primera actualización |

Sin `fecha_creacion`/`fecha_actualizacion` sueltas (regla ya aplicada en `usuarios` y
`catalogo_productos`: la fecha vive en `creado_por.fecha`/`actualizado_por.fecha`).

Embeber vs referenciar: colección raíz, referencia por `producto_codigo` (string), no por
`$ref`/`ObjectId` — permite mover/registrar ubicaciones sin depender de resolver primero el
`_id` de Mongo del producto. Historial de estados: no aplica.

### Índices propuestos

| Nombre | Campos | Tipo | Responde a |
|---|---|---|---|
| `uq_stock_ubicaciones_producto_ubicacion` | `producto_codigo` (1), `ubicacion` (1) | único compuesto | evita ubicaciones duplicadas para el mismo producto (bug real del legacy, sin índice) — también sirve como índice de consulta para "todas las ubicaciones de un producto" (prefijo del compuesto) |

No se agregan más índices en este incremento: todas las consultas de los 5 servicios (crear,
actualizar, eliminar, obtener producto con ubicaciones, transferir) resuelven con este único
índice compuesto — agregar otros sin una consulta concreta que los necesite violaría la regla
de `.claude/MONGODB.md` ("cada índice responde a una consulta concreta, no a intuición").

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/routers/productos.py::obtener_producto_con_ubicaciones, crear_ubicacion_producto, actualizar_ubicacion_producto, eliminar_ubicacion_producto, transferir_stock, obtener_stock_por_ubicacion` | Endpoints de ubicaciones, montados hoy bajo `/productos/...` | `infrastructure/api/routes.py` de `ubicaciones`, con su propio prefijo (p. ej. `/api/productos/{codigo}/ubicaciones` delegando al módulo, o `/api/ubicaciones` — a decidir en Fase 0) |
| `app/crud.py::get_producto_con_ubicaciones, crear_ubicacion, actualizar_ubicacion, eliminar_ubicacion, transferir_stock_entre_ubicaciones, crear_movimiento_ubicacion` | Persistencia y reglas de negocio de ubicaciones | `application/services/*` + `infrastructure/persistence/mongo/ubicacion_repository.py` |
| `app/crud.py::obtener_stock_con_reservas_por_ubicacion` | Cálculo de stock disponible considerando reservas | `application/services/calcular_stock_disponible.py` (colabora con el puerto de `reservas`) |

## Responsabilidades detectadas

- Crear ubicación con stock físico inicial, validando que no exceda el stock total del producto no asignado.
- Actualizar cantidad física de una ubicación, redistribuyendo el stock total del producto.
- Eliminar ubicación.
- Transferir stock entre dos ubicaciones del mismo producto, registrando un movimiento de tipo `transferencia_ubicacion`.
- Calcular stock disponible por ubicación (físico − reservado por otros − reservado por el usuario actual).

## Domain

- **Entities**: `Ubicacion` (producto_codigo, nombre_ubicacion, stock_fisico, stock_reservado, fecha_creacion).
- **Errors**: ubicación duplicada para el mismo producto, ubicación no encontrada, stock insuficiente para transferencia, stock excede el disponible del producto.

## Application

- **DTO**: `CrearUbicacionDTO`, `ActualizarUbicacionDTO`, `TransferenciaStockDTO`, `UbicacionDTO`, `StockDisponibleDTO`.
- **Ports**: `UbicacionRepositoryPort`, y colaboración con `ProductoRepositoryPort` (de `productos`) y un puerto de lectura de `reservas` (`ReservaLectoraPort`, para no acoplar `ubicaciones` al repositorio concreto de `reservas`).
- **Services**: `CrearUbicacionService`, `ActualizarUbicacionService`, `EliminarUbicacionService`, `TransferirStockService`, `ObtenerProductoConUbicacionesService`, `CalcularStockDisponibleService`.

## Infrastructure

- **Persistence**: `MongoUbicacionRepository` (colección `ubicaciones`). El legacy **no declara índices** para esta colección (a diferencia de `productos`/`movimientos`) — se debe proponer al menos un índice compuesto `(producto_codigo, ubicacion)` único en el modelado Fase 1.
- **API**: rutas bajo el módulo `ubicaciones` (definir prefijo en Fase 0).

## Bootstrap

`register_module(app)` registra el router de ubicaciones.

## Validaciones

- No permitir crear una ubicación duplicada para el mismo producto.
- Cantidad de transferencia debe ser `>= 1` y no exceder el stock físico de la ubicación origen.
- ~~Al actualizar cantidad física, la nueva suma de todas las ubicaciones no puede exceder `producto.stock_actual`~~ **ELIMINADA (decisión Fase 0):** ese techo asumía que `stock_actual` viene de una fuente independiente (`movimientos`, que no existe todavía). Con `stock_actual` recalculado desde cero como suma de `ubicaciones`, no hay techo que exceder — crear/actualizar solo valida `stock_fisico >= 0`. Se puede reintroducir un techo real basado en entradas/salidas cuando exista `movimientos`, si el negocio lo sigue necesitando.

## Riesgos

- ~~Consistencia distribuida sin transacción explícita...~~ **RESUELTO**: `ubicaciones` es ahora la fuente de verdad (decisión Fase 0), `productos.stock_actual` se recalcula desde cero (suma de `ubicaciones`) dentro de la misma transacción Mongo (`MongoUnitOfWork`, validado contra el replica set real — ver hallazgo al cierre del módulo `auth`). Confirmado con datos reales: varios de los 12 documentos de `ubicaciones` en `inventario_db` tienen `stock_fisico`/`stock_reservado` negativos — exactamente la clase de bug que la transacción nueva evita.
- ~~Sin índice único en `ubicaciones`, el legacy permite crear ubicaciones duplicadas...~~ **RESUELTO**: `uq_stock_ubicaciones_producto_ubicacion` (único compuesto) en la colección nueva.
- ~~`crud.py::crear_ubicacion` registra un movimiento... acopla `ubicaciones` a `movimientos`~~ **RESUELTO (decisión Fase 0)**: se omite esta responsabilidad en el incremento 1 (`movimientos` no existe todavía) — no se crea un `RegistradorMovimientoPort` prematuro, queda como deuda explícita para cuando se migre `movimientos`.

## Utilidades reutilizables

Ninguna.

## Refactorizaciones recomendadas

- ~~Introducir Unit of Work para las operaciones que actualizan `productos` + `ubicaciones`~~ **RESUELTO**: los 3 servicios que mutan ambas colecciones (`CrearUbicacionService`, `ActualizarUbicacionService`, `EliminarUbicacionService`) usan `MongoUnitOfWork`.
- El cálculo "stock disponible" quedó como una property simple (`stock_fisico - stock_reservado`) en la entidad `Ubicacion` — no hace falta un servicio dedicado en este incremento (sin `reservas`, no hay triplicación que eliminar; se reevalúa cuando exista ese módulo).

## Código que NO debe migrarse

- Los `try/except` desnudos (`except: pass`) usados para "intentar convertir a ObjectId" en varios endpoints — no aplica al diseño nuevo (identificador = `codigo`/`ubicacion`, sin ObjectId en rutas).

## Checklist de migración

- [x] Domain — `Ubicacion` (`crear`/`actualizar_stock_fisico`/`stock_disponible`), errores `UBIC-001/002/003`, 5 tests (+2 tests en `productos` para `Producto.recalcular_stock`)
- [x] Application — 3 DTOs, `UbicacionRepositoryPort`, 5 servicios (3 con `MongoUnitOfWork`), 18 tests
- [x] Infrastructure — `MongoUbicacionRepository` (propaga sesión de transacción), schema Mongo `stock_ubicaciones` sincronizado (1 índice único compuesto), 3 tests de regresión
- [x] API — rutas anidadas bajo `/api/productos/{codigo}/ubicaciones`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 26 tests unitarios nuevos + verificación end-to-end (33 casos) contra `inventario_db` real

## Incremento 1 — CRUD + transferencia (completo)

- **Cambio en `productos` (ya construido)**: `Producto.recalcular_stock(nuevo_stock_actual)` (distinto de `actualizar()`, que sigue sin tocar `stock_actual`). `ProductoRepositoryPort.actualizar()`/`MongoProductoRepository.actualizar()` ganan un parámetro opcional `uow` (retrocompatible) para participar en la misma transacción que la escritura de `ubicaciones`.
- **Domain**: `Ubicacion.crear()`, `actualizar_stock_fisico()`, property `stock_disponible`. Errores `UbicacionDuplicadaError` (409), `UbicacionNoEncontradaError` (404), `StockInsuficienteError` (400) — reutiliza `ProductoNoEncontradoError` de `productos` en vez de duplicar el concepto.
- **Application**: `UbicacionRepositoryPort` colabora con `ProductoRepositoryPort` de `productos` (import legítimo entre puertos de módulos distintos, no entre concretos). `CrearUbicacionService`/`ActualizarUbicacionService`/`EliminarUbicacionService` recalculan `stock_actual` como suma de todas las ubicaciones del producto, dentro de una transacción (`UnitOfWorkFactory`, inyectada como fábrica para no acoplar `application/` a `MongoUnitOfWork`). `TransferirStockService` no toca `productos` (el total no cambia, solo se redistribuye).
- **Infrastructure**: `MongoUbicacionRepository` propaga `uow.session` en `crear`/`actualizar`/`eliminar`/`listar_por_producto`. Rutas anidadas bajo `/api/productos/{codigo}/ubicaciones`, con `POST .../transferir` para la transferencia. Reutiliza `get_producto_repository` de `productos` en las dependencias (import infra↔infra entre módulos).

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Se probó el flujo completo con un usuario y un producto de prueba reales: crear 2 ubicaciones
(verificando que `stock_actual` del producto se recalcula como la suma tras cada una) →
duplicada (409) → producto inexistente (404) → actualizar cantidad física (200, `stock_actual`
recalculado) → actualizar inexistente (404) → transferir entre ubicaciones existentes (200,
`stock_actual` total sin cambios) → transferir a una ubicación nueva (se crea automáticamente)
→ transferir con stock insuficiente (400, `UBIC-003`) → transferir con origen inexistente (404)
→ eliminar ubicación vacía (200, `stock_actual` sin cambios) → eliminar de nuevo (404). Los 33
casos se comportaron como se diseñó, incluyendo la recalculación transaccional de
`stock_actual` contra el replica set real. `ubicaciones` (legacy, 12 documentos) y `productos`
(legacy, 6 documentos) verificados intactos antes y después. Suite completa: **121/121 tests
verdes**.

### Checklist del incremento 1

- [x] Domain — `Ubicacion` + 3 errores nuevos, 5 tests (+2 en `productos` para `recalcular_stock`)
- [x] Application — puerto, 5 servicios con soporte transaccional, 18 tests
- [x] Infrastructure — `MongoUbicacionRepository`, schema `stock_ubicaciones` sincronizado, 3 tests de regresión de propagación de sesión
- [x] Verificación end-to-end completa (33 casos) contra `inventario_db` real, con limpieza de datos de prueba

## Observaciones

Este módulo concentraba el riesgo de consistencia más alto de toda la migración porque el
stock total (`productos.stock_actual`) es una vista denormalizada de la suma de
`ubicaciones.stock_fisico`, y en el legacy ambas se actualizaban de forma manual y dispersa en
al menos 4 lugares distintos, sin transacción. **Resuelto**: `ubicaciones` es la fuente de
verdad, `productos.stock_actual` se recalcula desde cero dentro de una transacción Mongo real
(habilitada por la conversión a replica set, ver hallazgo al cierre de `auth`).

**Deuda explícita para cuando existan esos módulos**: registrar movimiento al crear/transferir
ubicación (`movimientos`, módulo #6), y cruzar `stock_disponible` contra reservas activas
(`reservas`, módulo #5). Ninguno de los dos se diseñó con puertos "no-op" prematuros — se
construyen cuando esos módulos existan.

**Siguiente módulo según la prioridad de migración**: `mercados_predefinidos` (depende de
`productos`, ya disponible; independiente de `reservas`/`movimientos`).

---

# Módulo `mercados_predefinidos`

## Objetivo

Mantener catálogos de "kits" de productos predefinidos (p. ej. "Mercado Básico", "Mercado
Grande") usados para agilizar salidas masivas de ayuda humanitaria sin tener que seleccionar
producto por producto.

## Fase 0 — Alcance acordado (WORKFLOW.md)

### Hallazgos confirmados contra el código legacy real (no solo el resumen del plan)

- **`crud.py::crear_mercado_predefinido`/`actualizar_mercado_predefinido` son código muerto a nivel de API.** Revisado `routers/movimientos.py` completo: los únicos endpoints reales son `GET /mercados`, `GET /mercados/{nombre}` y `POST /mercados/iniciar` — **ninguno protegido con autenticación**, ni siquiera comentada.
- **Datos reales de producción, distintos de lo que documenta el código**: `inventario_db.mercados_predefinidos` tiene **7 kits reales** (`KIT_BASICO`, `KIT_REFORZADO`, `KIT_ESPECIAL`, `KIT_AYUDA_HUMANITARIA`, `KIT_ESCOLAR_COLOMBIA`, `KIT_ESCOLAR_ESCUELES`, `KIT_ASEO`) — no `MERCADO_BASICO`/`MERCADO_GRANDE` (lo que sembraría `init_mercados_predefinidos`). Se crearon por otra vía, no por el flujo de código visible. Sin `creado_por`, sin índice único en `nombre` (confirmado: cero índices más allá de `_id_`) — mismo patrón de colisión que `users`, `productos` y `ubicaciones`.
- **`producto_nombre` denormalizado y ya desactualizado en los datos reales**: los 7 kits referencian `producto_id: "100"` con `producto_nombre: "harina"`, pero en la colección `productos` real ese código hoy es `"ARROZ"`. El legacy nunca revalida ese nombre cacheado.

### Decisiones

| Pregunta | Decisión |
|---|---|
| Alcance del **primer incremento** | **CRUD completo**: `CrearMercadoPredefinidoService`, `ActualizarMercadoPredefinidoService`, `ListarMercadosPredefinidosService`, `ObtenerMercadoPredefinidoService`. Módulo simple y aislado (bajo riesgo), no se justifica dividirlo más. |
| Validación de `producto_id` en crear/actualizar | **Se valida contra `catalogo_productos`** (vía `ProductoRepositoryPort`) y el nombre se resuelve en vivo desde el producto real — corrige el bug de nombres desactualizados encontrado en los datos reales. Si el código no existe, error de dominio (no se guarda el mercado). |
| Autenticación en endpoints de escritura | **Todos los endpoints de escritura** (crear, actualizar) requieren `require_authenticated`, mismo criterio que `productos`/`ubicaciones`. Lectura (listar, obtener por nombre) queda sin autenticación, igual que hoy. |
| Prefijo de rutas | `/api/mercados-predefinidos` — se saca del prefijo `/movimientos` (mezcla de dominios ya señalada como refactor recomendado en este mismo documento). |

Con esto, el **checklist de Fase 0** de `.claude/WORKFLOW.md` queda completo. Sigue la Fase 1
(modelado de la colección en Mongo) antes de escribir cualquier código — incluyendo la
verificación de colisión con `mercados_predefinidos` real (ya hecha arriba) y la decisión de
nombre de colección aislada.

## Fase 1 — Modelado MongoDB (colección `catalogo_mercados_predefinidos`) — *(propuesta, pendiente de aprobación)*

Mismo criterio que `auth`/`productos`/`ubicaciones`: colección aislada, sin tocar los 7 kits
reales de `mercados_predefinidos` (legacy).

### Estructura del documento

| Campo | Tipo (bsonType) | Obligatorio | Notas |
|---|---|---|---|
| `_id` | objectId | sí | id técnico |
| `nombre` | string | sí | único (índice nuevo — el legacy no lo tenía) |
| `descripcion` | string\|null | no | |
| `productos` | array de objetos `{producto_id, cantidad, producto_nombre}` | sí | no vacío (validado en domain/DTO); `producto_nombre` se resuelve en vivo desde `catalogo_productos` al crear/actualizar (decisión Fase 0), pero se guarda desnormalizado para lectura sin joins (mismo criterio que el legacy, corrigiendo que ahora sí se mantiene actualizado en cada escritura) |
| `activo` | bool | sí | default `true` |
| `creado_por` | object (`AuditPersona`) | sí | |
| `actualizado_por` | object (`AuditPersona`) | no | nulo hasta la primera actualización |

Sin `created_at`/`updated_at` sueltos (mismo criterio ya aplicado: la fecha vive en
`creado_por.fecha`/`actualizado_por.fecha`). Embeber vs referenciar: `productos` embebido
(lista corta, siempre se lee junto con el mercado, nunca por separado) — referencia por
`producto_id` (string) a `catalogo_productos`, sin `$ref`.

### Índices propuestos

| Nombre | Campos | Tipo | Responde a |
|---|---|---|---|
| `uq_catalogo_mercados_predefinidos_nombre` | `nombre` (1) | único | obtener por nombre, evita duplicados (bug real corregido) |

No se agrega índice sobre `activo`: la colección es de tamaño pequeño por naturaleza (catálogo
de kits, no transaccional) — un filtro por `activo` sin índice es trivial a esta escala, y
agregar uno sin una necesidad de performance concreta violaría la regla de `.claude/MONGODB.md`.

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/crud.py::get_mercados_predefinidos, get_mercado_predefinido, crear_mercado_predefinido, actualizar_mercado_predefinido, init_mercados_predefinidos` | Persistencia de mercados predefinidos | `application/services/*` + `infrastructure/persistence/mongo/mercado_predefinido_repository.py` |
| `app/routers/movimientos.py::get_mercados, get_mercado_por_nombre, init_mercados` | Endpoints de consulta/inicialización | `infrastructure/api/routes.py` |
| `app/models.py::MercadoPredefinido, MercadoPredefinidoCreate` | Entidad y DTO | `domain/entities/mercado_predefinido.py` + `application/dto/` |

## Responsabilidades detectadas

- CRUD de mercados predefinidos (nombre, descripción, lista de productos con cantidad, activo/inactivo).
- Inicialización con datos semilla (Mercado Básico/Grande) — **utilidad de seed, no lógica de negocio de producción**.

## Domain

- **Entities**: `MercadoPredefinido` (nombre, descripcion, productos: lista de {producto_id, cantidad, producto_nombre}, activo, created_at, updated_at, created_by).
- **Errors**: mercado no encontrado, nombre duplicado, lista de productos vacía.

## Application

- **DTO**: `CrearMercadoPredefinidoDTO`, `ActualizarMercadoPredefinidoDTO`, `MercadoPredefinidoDTO`.
- **Ports**: `MercadoPredefinidoRepositoryPort`.
- **Services**: `CrearMercadoPredefinidoService`, `ActualizarMercadoPredefinidoService`, `ListarMercadosPredefinidosService`, `ObtenerMercadoPredefinidoService`.

## Infrastructure

- **Persistence**: `MongoMercadoPredefinidoRepository` (colección `mercados_predefinidos`); el legacy no declara índices — proponer único en `nombre`.
- **API**: rutas `/api/mercados-predefinidos` (o el prefijo que se acuerde; hoy viven, de forma confusa, bajo `/movimientos/mercados`).

## Bootstrap

`register_module(app)` registra el router.

## Validaciones

- `productos`: lista no vacía, cada ítem con `producto_id` y `cantidad > 0`.
- **Nuevo (decisión Fase 0)**: cada `producto_id` debe existir en `catalogo_productos`; el `producto_nombre` se resuelve en vivo, no se confía en el que manda el cliente.
- `nombre`: no vacío, único (nuevo índice — el legacy no lo tenía).

## Riesgos

- Bajo en términos de lógica de negocio, pero **confirmado con datos reales**: colisión con 7 kits de producción reales en `mercados_predefinidos` (`KIT_BASICO`, `KIT_REFORZADO`, etc. — no los `MERCADO_BASICO`/`GRANDE` que documenta el código), sin `creado_por` ni índice único en `nombre`. Mismo criterio de resolución que `users`/`productos`/`ubicaciones`: colección aislada (ver Fase 1).
- `producto_nombre` denormalizado ya desactualizado en los 7 kits reales (ej. código `"100"` cacheado como `"harina"`, hoy es `"ARROZ"` en `productos`) — resuelto en el diseño nuevo validando y resolviendo el nombre en vivo (ver Fase 0).
- ~~La semilla de datos (`init_mercados_predefinidos`) tiene productos hardcodeados...~~ **Confirmado como no aplicable**: los datos reales de producción (7 kits) no coinciden con esa semilla — no hay necesidad de migrar `init_mercados_predefinidos` ni sus datos hardcodeados.

## Utilidades reutilizables

Ninguna.

## Refactorizaciones recomendadas

- Mover el endpoint de consulta fuera del prefijo `/movimientos` (mezcla de dominios en el router legacy).

## Código que NO debe migrarse

- El endpoint `init_mercados` como endpoint público de producción — si se necesita sembrar datos, debe ser un script de datos, no un endpoint HTTP accesible sin autenticación (el legacy no lo protege).

## Checklist de migración

- [x] Domain — `MercadoPredefinido` + `ProductoKit`, errores `MERC-001/002/003`
- [x] Application — 3 DTOs, `MercadoPredefinidoRepositoryPort`, 4 servicios, 16 tests
- [x] Infrastructure — `MongoMercadoPredefinidoRepository`, schema `catalogo_mercados_predefinidos` sincronizado (1 índice único)
- [x] API — `GET/POST /api/mercados-predefinidos`, `GET/PUT /api/mercados-predefinidos/{nombre}`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 21 tests unitarios (5 dominio + 16 aplicación) + verificación end-to-end (22 casos) contra `inventario_db` real

## Incremento 1 — CRUD completo (completo)

- **Domain**: `MercadoPredefinido.crear()`/`actualizar()` (update parcial, `nombre` no editable), value object `ProductoKit` embebido. Ambos métodos rechazan una lista de productos vacía (`MercadoProductosVacioError`).
- **Application**: `CrearMercadoPredefinidoService`/`ActualizarMercadoPredefinidoService` colaboran con `ProductoRepositoryPort` (de `productos`) para validar cada `producto_id` y resolver `producto_nombre` en vivo — corrige el bug real de nombres desactualizados encontrado en los 7 kits de producción (`producto_id: "100"` cacheado como `"harina"`, hoy `"ARROZ"` en `productos`). `ListarMercadosPredefinidosService` sin paginar (catálogo chico por naturaleza).
- **Infrastructure**: `MongoMercadoPredefinidoRepository` sobre `catalogo_mercados_predefinidos` (colección aislada). Rutas `/api/mercados-predefinidos` (fuera del prefijo `/movimientos` del legacy), escritura protegida con `require_authenticated`.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Se crearon 2 productos y un mercado de prueba reales: crear sin auth (401) → crear con
producto inexistente (404, `PROD-002`) → crear real (201, `producto_nombre` resuelto en vivo,
no el que mandó el cliente) → duplicado (409, `MERC-001`) → obtener por nombre (200) →
inexistente (404, `MERC-002`) → listar activos (lo incluye) → actualizar sin auth (401) →
desactivar (200) → listar activos ya no lo incluye, listar todos sí → actualizar productos
(nombres re-resueltos en vivo) → actualizar con producto inexistente (404) → actualizar
mercado inexistente (404). Los 22 casos se comportaron como se diseñó. `mercados_predefinidos`
(legacy, 7 kits reales) verificado intacto antes y después. Suite completa: **137/137 tests
verdes**.

### Checklist del incremento 1

- [x] Domain — `MercadoPredefinido` + `ProductoKit` + 3 errores nuevos, 5 tests
- [x] Application — puerto, 4 servicios (2 con resolución en vivo contra `productos`), 16 tests
- [x] Infrastructure — `MongoMercadoPredefinidoRepository`, schema sincronizado (1 índice único en `nombre`, gap real del legacy corregido)
- [x] Verificación end-to-end completa (22 casos) contra `inventario_db` real, con limpieza de datos de prueba

## Observaciones

**Siguiente módulo según la prioridad de migración**: `reservas` (depende de `productos` y
`ubicaciones`, ambos ya disponibles) — aunque `mercados_predefinidos` en sí no depende de
`ubicaciones`/`reservas`/`movimientos`, sí es referenciado eventualmente por `movimientos`
(salida por mercado, ver `routers/movimientos.py::salida_por_mercado`, fuera de alcance de
este módulo).

---

# Módulo `reservas`

## Objetivo

Permitir que un usuario "aparte" temporalmente stock de uno o más productos/ubicaciones
mientras arma una salida (carrito de trabajo por sesión), evitando que dos usuarios
concurrentes sobre-comprometan el mismo stock físico antes de confirmar la salida real.

## Fase 0 — Alcance acordado (WORKFLOW.md)

### Hallazgos confirmados contra el código legacy real y Mongo

- **Descubrimiento arquitectónico clave**: el legacy mantiene DOS mecanismos paralelos para "stock reservado". `ubicaciones.stock_reservado` es un contador cacheado que `guardar_reserva`/`ajustar_reserva`/`eliminar_reserva` incrementan/decrementan con `$inc` — es el mismo contador que ya vimos con valores negativos reales al investigar `ubicaciones`. Pero el cálculo real de "stock disponible" que ve el usuario (`obtener_stock_con_reservas`, `obtener_stock_con_reservas_por_ubicacion`) **no lee ese contador** — recalcula en vivo, sumando las `reservas` activas en el momento de la consulta. El contador cacheado es peso muerto que además se corrompe.
- **Confirmado con datos reales**: hay **3 reservas abandonadas en producción** (de abril y junio, meses de antigüedad) que nunca se confirmaron ni cancelaron — el riesgo de "reservas abandonadas bloquean stock indefinidamente" que ya anotaba el plan está ocurriendo activamente, no es teórico.
- **Dato del plan desactualizado**: el legacy **sí** tiene índice único en `session_id` (`session_id_1`) — el plan decía que no existía índice alguno.
- `guardar_reserva` (siempre suma) y `ajustar_reserva` (suma o resta, elimina items en 0, elimina la reserva completa si no quedan items) son, en esencia, la misma operación con distinto signo — duplican ~80% de la lógica de reconstrucción de diccionarios que el propio plan marca como el mayor riesgo de bugs del módulo.
- Ninguno de los endpoints de `reservas` (`guardar`, `obtener`, `eliminar`, `ajustar`, `stock-disponible`) tiene autenticación en el legacy, ni comentada.
- `confirmar_reserva`/`confirmar-multiples` viven en `routers/movimientos.py` y operan sobre reservas, pero son responsabilidad de `movimientos` (generan la salida real) — confirmado, fuera de alcance de este módulo (ver Observaciones).

### Decisiones

| Pregunta | Decisión |
|---|---|
| Arquitectura de "stock reservado" | **Solo cálculo en vivo** (recomendado): `reservas` no escribe nada en `ubicaciones`. `stock_disponible` se calcula sumando reservas activas contra `ubicaciones.stock_fisico` al momento de la consulta. Elimina la clase de bug de contador desincronizado; permite usar un TTL index sin efectos secundarios (no hay contador en otra colección que quede huérfano). `stock_reservado` en `stock_ubicaciones` (módulo `ubicaciones`) queda confirmado como no usado — no se revierte esa decisión ahora, se deja documentado. |
| `guardar_reserva`/`ajustar_reserva` | **Unificados en un solo `AjustarReservaService`**: recibe items con cantidad con signo (positiva = agregar, negativa = quitar). Elimina la duplicación de lógica de reconstrucción de items. |
| Asociación con usuario autenticado | **Sí**: todos los endpoints de escritura requieren `require_authenticated`; la reserva guarda también el id del usuario que la creó, además de `session_id` (que sigue siendo la clave del carrito por pestaña/dispositivo). |
| TTL de reservas abandonadas | **3 días de inactividad** (`expireAfterSeconds`). Requiere un campo dedicado `ultima_actividad` (no reutiliza `creado_por.fecha`/`actualizado_por.fecha`, que no cubren el caso "nunca actualizada" de forma consistente para un índice TTL) — se actualiza en cada mutación de la reserva. |
| Alcance del incremento 1 | `AjustarReservaService` (unificado), `ObtenerReservaService`, `EliminarReservaService`, `CalcularStockDisponibleService`. **Fuera de alcance**: confirmar reserva como salida real (`movimientos`, no existe todavía). |

Con esto, el **checklist de Fase 0** de `.claude/WORKFLOW.md` queda completo. Sigue la Fase 1
(modelado de la colección en Mongo) — incluyendo la verificación de colisión con `reservas`
real (ya hecha arriba: 3 documentos reales, colección con datos abandonados pero reales).

## Fase 1 — Modelado MongoDB (colección `reservas_stock`) — *(propuesta, pendiente de aprobación)*

Mismo criterio que los módulos anteriores: colección aislada, sin tocar las 3 reservas reales
(abandonadas) de `reservas` (legacy).

### Estructura del documento

| Campo | Tipo (bsonType) | Obligatorio | Notas |
|---|---|---|---|
| `_id` | objectId | sí | |
| `session_id` | string | sí | único; identifica el carrito por pestaña/dispositivo |
| `items` | array de `{producto_codigo, ubicacion, cantidad}` | sí | sin denormalizar `producto_nombre`/`stock_actual` (decisión: se resuelven en vivo al leer, evita el mismo bug de datos desactualizados ya corregido en `mercados_predefinidos`); `ubicacion` obligatoria por item (a diferencia del legacy, que permitía omitirla) |
| `datos_adicionales` | object\|null | no | libre, sin schema fuerte — contexto de negocio (cliente, notas, caso) que `movimientos` usará al confirmar; no se valida su forma en este incremento |
| `creado_por` | object (`AuditPersona`) | sí | `id_persona` = usuario autenticado dueño del carrito (decisión Fase 0) |
| `actualizado_por` | object (`AuditPersona`) | no | nulo hasta el primer ajuste |
| `ultima_actividad` | date | sí | campo dedicado para el TTL index (no reutiliza `creado_por.fecha`/`actualizado_por.fecha`) — se actualiza en cada mutación |

Un documento persistido nunca tiene `items` vacío: si el último item llega a cantidad 0, se
elimina el documento completo (mismo comportamiento que el legacy).

### Índices propuestos

| Nombre | Campos | Tipo | Responde a |
|---|---|---|---|
| `uq_reservas_stock_session_id` | `session_id` (1) | único | identificador del carrito (ya existía en el legacy, se re-declara) |
| `idx_reservas_stock_items_producto_codigo` | `items.producto_codigo` (1) | normal | calcular reservas activas de un producto (mismo índice que tenía el legacy) |
| `ttl_reservas_stock_ultima_actividad` | `ultima_actividad` (1) | TTL, `expireAfterSeconds=259200` (3 días) | auto-expira carritos abandonados — decisión Fase 0, resuelve el problema confirmado con datos reales |

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/crud.py::guardar_reserva, obtener_reserva, eliminar_reserva, ajustar_reserva, obtener_stock_con_reservas` | Lógica de reservas por sesión | `application/services/*` + `infrastructure/persistence/mongo/reserva_repository.py` |
| `app/routers/movimientos.py::guardar_reserva_endpoint, obtener_reserva_endpoint, eliminar_reserva_endpoint, obtener_stock_disponible, ajustar_reserva_endpoint` | Endpoints, montados hoy bajo `/movimientos/reservas/*` | `infrastructure/api/routes.py` de `reservas`, prefijo propio (`/api/reservas`) |
| `app/models.py::Reserva, ReservaCreate, ReservaResponse` | Entidad y DTOs | `domain/entities/reserva.py` + `application/dto/` |

## Responsabilidades detectadas

- Crear/actualizar una reserva por `session_id`, acumulando cantidades si el producto+ubicación ya estaba reservado.
- Incrementar `stock_reservado` en la ubicación correspondiente al reservar.
- Liberar `stock_reservado` al eliminar o ajustar (con diferencias negativas) una reserva.
- Calcular stock disponible = físico − reservado por otras sesiones − reservado por la sesión actual.

## Domain

- **Entities**: `Reserva` (session_id, items: lista de {producto_id, producto_nombre, producto_codigo, ubicacion, cantidad, ...}, tipo, datos_adicionales, fecha_creacion, fecha_actualizacion).
- **Errors**: reserva no encontrada, item inválido (falta producto_id/cantidad), cantidad no positiva.

## Application

- **DTO**: `AjustarReservaDTO` (unificado, decisión Fase 0), `ReservaDTO`, `StockDisponibleDTO`.
- **Ports**: `ReservaRepositoryPort`, colaboración de **solo lectura** con `ProductoRepositoryPort`/`UbicacionRepositoryPort` (decisión Fase 0: sin escritura cruzada a `ubicaciones`, cálculo en vivo).
- **Services**: `AjustarReservaService` (unificado, reemplaza `GuardarReservaService`/`AjustarReservaService` separados), `ObtenerReservaService`, `EliminarReservaService`, `CalcularStockDisponibleService`.

## Infrastructure

- **Persistence**: `MongoReservaRepository` (colección `reservas` en el legacy). ~~El legacy no declara índice~~ **corregido**: sí tiene único en `session_id` (`session_id_1`, confirmado en Fase 0). Se agrega TTL index (`ultima_actividad`, 3 días) en el diseño nuevo.

## Bootstrap

`register_module(app)` registra el router.

## Validaciones

- Cada item de `items` debe traer `producto_id` y `cantidad > 0`.
- `session_id` obligatorio.

## Riesgos

- Es el módulo con la lógica más intrincada de manipulación de diccionarios del legacy (`guardar_reserva`, `ajustar_reserva` construyen y reconstruyen un diccionario indexado por `producto_id|ubicacion` a mano). **Decisión Fase 0**: unificados en un solo `AjustarReservaService` (cantidad con signo), reduciendo la superficie a testear. Sigue requiriendo pruebas unitarias exhaustivas de los casos: item nuevo, item existente que suma, item que baja a 0 (debe eliminarse), reserva completa sin items restantes (debe eliminarse el documento completo).
- ~~`session_id` no está atado a un usuario autenticado...~~ **RESUELTO (decisión Fase 0)**: se asocia también al usuario autenticado (`require_authenticated` en escritura + `usuario_id` guardado).
- ~~No hay expiración/TTL de reservas abandonadas...~~ **RESUELTO (decisión Fase 0)**: TTL index de 3 días sobre un campo dedicado `ultima_actividad`. Confirmado con datos reales que el problema ya está ocurriendo (3 reservas abandonadas de meses de antigüedad en `inventario_db.reservas`).
- **Nuevo hallazgo (Fase 0)**: el contador `ubicaciones.stock_reservado` del legacy es redundante y se corrompe (ver Fase 0) — resuelto por diseño al no replicarlo (cálculo en vivo).

## Utilidades reutilizables

Ninguna.

## Refactorizaciones recomendadas

- ~~Reemplazar la reconstrucción manual de diccionarios por operaciones atómicas de Mongo...~~ **Superado por la decisión Fase 0**: al no cachear un contador en `ubicaciones`, no hay operación atómica cross-colección que coordinar para "stock reservado" — solo la propia colección `reservas` se escribe.
- ~~Evaluar TTL index...~~ **Decidido en Fase 0**: 3 días.

## Código que NO debe migrarse

- El contador `ubicaciones.stock_reservado` y toda la lógica que lo mantiene (`$inc` en `guardar_reserva`/`ajustar_reserva`/`eliminar_reserva`) — confirmado como redundante y no usado por el cálculo real de stock disponible (ver Fase 0).

## Checklist de migración

- [x] Domain — `Reserva` + `ItemReserva`, errores `RES-001/002/003`
- [x] Application — 3 DTOs, `ReservaRepositoryPort`, 4 servicios (`AjustarReservaService` unificado + `CalcularStockDisponibleService` + `ObtenerReservaService` + `EliminarReservaService`), 25 tests
- [x] Infrastructure — `MongoReservaRepository`, schema `reservas_stock` sincronizado (único en `session_id`, índice en `items.producto_codigo`, **TTL de 3 días**)
- [x] API — `GET /api/reservas/stock-disponible/{producto_codigo}/{ubicacion}`, `GET/POST /api/reservas/{session_id}` (`/ajustar`), `DELETE /api/reservas/{session_id}` (solo `super_admin`)
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 34 tests unitarios (9 dominio + 25 aplicación) + verificación end-to-end (22 casos funcionales) contra `inventario_db` real

## Incremento 1 — Ajustar/consultar/eliminar reserva (completo)

- **Domain**: `Reserva.crear()` (rechaza items vacíos) y `Reserva.aplicar_ajuste()` (un item por llamada, delta con signo — reemplaza `guardar_reserva`/`ajustar_reserva` del legacy). Property `sin_items` para que el service decida si debe borrar el documento completo.
- **Application**: **decisión de arquitectura clave** — `stock_disponible` se calcula en vivo (`CalcularStockDisponibleService`, suma reservas activas contra `ubicaciones.stock_fisico`), sin mantener ningún contador cacheado cruzado con `ubicaciones` (a diferencia del legacy, cuyo contador `stock_reservado` se confirmó redundante y corrupto). `AjustarReservaService` valida stock disponible antes de aceptar cualquier ajuste positivo (`StockDisponibleInsuficienteError`) — corrige que el legacy nunca validaba esto, pese a ser el objetivo declarado del módulo. Permisos por rol acordados con el desarrollador: `AjustarReservaService`/`ObtenerReservaService`/`CalcularStockDisponibleService` → `require_authenticated`; `EliminarReservaService` → `require_super_admin` únicamente (mismo criterio que tendrá "confirmar reserva" en `movimientos`).
- **Infrastructure**: `MongoReservaRepository`. Schema con **TTL index de 3 días sobre `ultima_actividad`** (campo dedicado, no reutiliza `creado_por.fecha`) — resuelve de raíz el problema confirmado con datos reales de reservas abandonadas, sin dejar contadores huérfanos en otra colección (porque no existen).
- **Bug real encontrado y corregido durante la verificación**: `routes.py::ajustar_reserva` pasaba los objetos `AjusteItemRequest` (schema HTTP) directo al DTO de aplicación `AjustarReservaInput`, que espera `AjusteItemInput` — Pydantic v2 no convierte automáticamente entre dos clases `BaseModel` distintas aunque sean estructuralmente iguales. Se corrigió mapeando explícitamente cada item, mismo patrón que ya se usa en `mercados_predefinidos`.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Se probó el flujo completo con 2 usuarios reales (uno operativo, uno promovido a `super_admin`
directo en Mongo, mismo criterio que en `auth`), un producto y una ubicación con 100 unidades
de stock real: stock disponible inicial (100) → ajustar sin auth (401) → crear reserva nueva
con 10 unidades (200, `datos_adicionales` guardado) → stock disponible baja a 90 tanto para
otras sesiones como para la propia (confirma que `reservado_actual` se resta por separado) →
reservar más de lo disponible (400, `RES-003`) → obtener reserva (200) → obtener inexistente
(404) → sumar a la reserva existente (15) → restar toda la cantidad (200, mensaje de
eliminación, confirma que el documento se borra) → obtener tras vaciar (404) → stock disponible
vuelve a 100 → recrear reserva → eliminar sin auth (401) → eliminar con operativo (**403**,
confirma el permiso exclusivo de `super_admin`) → eliminar con `super_admin` (200) → eliminar
de nuevo (404). Los 22 casos funcionales se comportaron como se diseñó (más 4 conflictos de
setup de una corrida anterior interrumpida por el bug ya corregido, no relacionados con la
lógica de negocio). `reservas` (legacy, 3 documentos reales abandonados) verificado intacto
antes y después. Suite completa: **162/162 tests verdes**.

### Checklist del incremento 1

- [x] Domain — `Reserva` + `ItemReserva` + 3 errores nuevos, 9 tests
- [x] Application — puerto, 4 servicios, 25 tests
- [x] Infrastructure — `MongoReservaRepository`, schema sincronizado con TTL, bug de mapeo DTO↔schema corregido
- [x] Verificación end-to-end completa (22 casos funcionales) contra `inventario_db` real, con limpieza de datos de prueba

## Observaciones

Este módulo es un prerrequisito funcional de `movimientos` (específicamente de
`reservas/confirmar`, que en el legacy vive erróneamente dentro de `routers/movimientos.py`
pero opera sobre reservas). Ver módulo `movimientos` para el flujo de confirmación —
**confirmar reserva queda fuera del alcance del incremento 1** de este módulo.

**Contexto de permisos para `movimientos` (confirmado con el desarrollador, aplica a futuro)**:
el rol `operativo` solo hace reservas y "entradas previas" (probablemente mapea a
`entradas_pendientes` del módulo `aprobaciones_pendientes`); el rol `admin` es de solo lectura
(inventario, productos, informes de movimientos); **`super_admin` es el único que confirma
tanto entradas como reservas** (que se convierten en salidas) — mismo criterio ya aplicado acá
para `EliminarReservaService`. Esto es jerárquico sobre los 3 roles ya existentes en `auth`, no
requirió cambios en `productos`/`ubicaciones`/`mercados_predefinidos` (que siguen con
`require_authenticated` genérico para escritura).

**Siguiente módulo según la prioridad de migración**: `movimientos` (depende de `productos`,
`ubicaciones`, `reservas` y `mercados_predefinidos`, todos ya disponibles) — es el módulo más
complejo y el que más lógica de negocio concentra, según el propio plan.

---

# Módulo `movimientos`

## Objetivo

Registrar toda entrada y salida de inventario (individual, múltiple, por kit, por mercado
predefinido), manteniendo la trazabilidad completa (remisión, caso, usuario, comprobante PDF)
y siendo la única vía legítima de alterar `productos.stock_actual` y `ubicaciones.stock_fisico`.

## Fase 0 — Alcance acordado (WORKFLOW.md)

### Hallazgos confirmados contra el código legacy (no solo el resumen del plan)

- **`crear_salida_multiple` nunca toca `ubicaciones`** (hallazgo nuevo, no estaba en la versión
  anterior de este plan): solo decrementa `productos.stock_actual`. Si se usa, `stock_actual` y
  la suma de `ubicaciones.stock_fisico` quedan desincronizados de inmediato — un bug adicional
  al ya documentado en `crear_movimiento`/`crear_entrada_multiple` (actualizaciones sueltas sin
  transacción).
- **`generar_numero_remision` no es atómico**: hace `find_one` + `update_one` separados (no
  `$inc` vía `find_one_and_update`) — dos salidas concurrentes pueden recibir el mismo número de
  remisión. Confirmado como race condition real, no solo teórica.
- **Colisión confirmada contra `inventario_db` real** (verificado en modo lectura): `movimientos`
  tiene **58 documentos reales**, `contadores` tiene **1 documento real** (`remision`,
  `ultimo_numero: 23`). Mismo patrón que todos los módulos anteriores → colecciones aisladas.
- **Los documentos reales tienen campos que ningún modelo Pydantic del legacy declara**:
  `usuario_id`, `caso`, `numero_cajas`, `es_kit`, `kit_nombre`, `productos_kit`, `es_multiple`,
  `productos_multiple`, `es_entrada_multiple`, `es_kit_mercado`, `nombre_mercado` — se construyen
  como `dict` a mano en `crud.py`/el router, nunca pasan por `Movimiento`/`MovimientoCreate`. La
  entidad de dominio nueva debe reflejar la forma real persistida, no los modelos Pydantic
  (que están incompletos).
- **Distribución real de uso por modalidad** (de los 58 documentos): `es_kit=True` → **23**,
  `es_entrada_multiple=True` → **3**, `es_multiple=True` → **0**, `es_kit_mercado=True` → **0**.
  Es decir, la confirmación de reserva modalidad **kit** es, con diferencia, la más usada en
  producción — y la salida múltiple directa (`crear_salida_multiple`) y la salida por mercado
  (`salida_por_mercado`) **nunca se usaron**. Esto invierte la prioridad ingenua del plan
  original (que proponía kit/mercado al final).
- **`tipo` en los datos reales incluye además `creacion_ubicacion` y `transferencia_ubicacion`**
  — bitácora que el legacy de `ubicaciones` escribía en esta misma colección. El módulo
  `ubicaciones` nuevo (ya cerrado) no escribe en ninguna colección de movimientos hoy.

### Inconsistencia entre módulos ya construidos (resuelta con el desarrollador)

`ReservaRepositoryPort.eliminar`/`actualizar` (módulo `reservas`, ya cerrado) no aceptan `uow`,
a diferencia de `UbicacionRepositoryPort`/`ProductoRepositoryPort`. `ConfirmarReservaService`
necesita que la eliminación/ajuste de la reserva participe de la misma transacción que el
descuento de stock. **Decisión:** se extiende `ReservaRepositoryPort` (parámetro `uow` opcional
en `eliminar`/`actualizar`, mismo patrón que los otros puertos) — cambio chico y aislado, no
reabre ninguna otra parte de `reservas`.

### Decisiones cerradas con el desarrollador

| Pregunta | Decisión |
|---|---|
| Orden de construcción | **Por uso real, no por el orden ingenuo del plan original** (ver Plan de incrementos abajo). Kit (23/58) va antes de múltiple/mercado (0/58 cada uno). |
| Permisos de creación **directa** de movimiento (no confirmación de reserva) | **Depende del tipo**: entrada directa (`RegistrarEntradaService`, `RegistrarEntradaMultipleService`) → `require_authenticated` (bajo riesgo, análogo a una "entrada previa"). Salida directa (`RegistrarSalidaService`) → `require_super_admin` (coherente con "solo super_admin aplica cambios reales de stock"). Confirmación de reserva (cualquier modalidad) → `require_super_admin`, ya decidido en el módulo `reservas`. |
| Salida múltiple directa y salida por mercado (0 usos reales, la segunda con bug de función inexistente) | **Se incluyen igual, rediseñadas** — como incremento final de baja prioridad, no se descartan del alcance del módulo. |
| Nombres de colección aislada | **`registro_movimientos`** (no `movimientos`) y **`contadores_movimientos`** (no `contadores`) — mismo criterio que `usuarios`/`catalogo_productos`/`stock_ubicaciones`/`reservas_stock`/`catalogo_mercados_predefinidos`. |
| Puerto `ReservaRepositoryPort` sin `uow` | Se extiende ahora (ver arriba) — necesario para que `ConfirmarReservaService` sea atómico desde el día uno. |
| Bitácora de `ubicaciones` en `movimientos` (tipos `creacion_ubicacion`/`transferencia_ubicacion`) | **Se agrega al alcance**, pero como incremento propio y posterior al núcleo — ver Plan de incrementos. Aplica a `CrearUbicacionService` y `TransferirStockService` (los dos que aparecen en los datos reales); `ActualizarUbicacionService`/`EliminarUbicacionService` quedan fuera (no tienen precedente en los datos reales). |
| Ciclo de dependencia `movimientos↔ubicaciones` que introduce la bitácora | **Inversión de dependencias**: `ubicaciones` define y posee `RegistradorDeMovimientosPort` (nombre a confirmar en Fase 2 de ese incremento); `movimientos` provee el adaptador concreto, cableado únicamente en `shared/bootstrap/application.py`. Ningún módulo importa código interno del otro — se preserva el DAG de dependencias del plan general. |

### Plan de incrementos (este módulo se construye en 6 incrementos, no de una vez)

1. **Núcleo** — `RegistrarEntradaService`/`RegistrarSalidaService` (movimiento individual,
   separados por el permiso distinto), `ListarMovimientosService`, `ExportarMovimientosExcelService`,
   `GeneradorSecuencialPort` con `find_one_and_update`/`$inc` atómico (corrige la race condition).
   Crea las colecciones `registro_movimientos`/`contadores_movimientos`.
2. **Confirmar reserva — modalidad normal** — colabora con `reservas`+`ubicaciones`+`productos`
   vía `MongoUnitOfWork`; requiere la extensión de `ReservaRepositoryPort` (ver arriba).
3. **Confirmar reserva — modalidad kit** (23/58 usos reales, la más usada) — incluye
   `ComprobantePort`/adaptador `reportlab`, `SubirPdfFirmadoService`, `ObtenerInfoPdfService`.
4. **Entrada múltiple directa** — `RegistrarEntradaMultipleService` (3/58 usos reales).
5. **Bitácora de `ubicaciones`** — reabre el módulo `ubicaciones` para que `CrearUbicacionService`/
   `TransferirStockService` emitan un registro vía `RegistradorDeMovimientosPort` (inversión de
   dependencias, ver arriba). Incremento independiente del núcleo — puede construirse en cualquier
   momento después de tener `registro_movimientos` creada y validada.
6. **Baja prioridad (0/58 usos reales, rediseñadas)** — confirmar reserva modalidad múltiple,
   salida múltiple directa (`crear_salida_multiple`), salida por mercado (`salida_por_mercado`,
   corrigiendo la llamada a `get_ubicaciones_producto` inexistente), y el rediseño completo de
   "confirmar varias reservas en un comprobante" (el legacy nunca lo implementó — no hay
   comportamiento real que preservar, se diseña de cero si en algún momento hay demanda real).

### Puertos module-scoped por precedente (no `shared/`, por ahora)

Mismo criterio que `EmailSenderPort` en `auth` (se queda en el módulo hasta que aparezca un
segundo consumidor real):

- `GeneradorSecuencialPort` — hoy solo lo usa `movimientos` (remisión). Candidato a
  generalizarse a "secuencia con prefijo" reutilizable si otro módulo lo necesita.
- `ComprobantePort` — hoy solo lo usa `movimientos`.
- `StorageRepositoryPort` — la tabla general de candidatos lo marcaba para `productos` (imágenes)
  y `movimientos` (PDFs), pero `productos` **todavía no construyó** la subida de imágenes (quedó
  diferida en su Fase 0). `movimientos` sería hoy su único consumidor real → se queda en
  `modules/movimientos/application/ports/`, no en `shared/`, hasta que `productos` lo necesite
  de verdad.

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino propuesto |
|---|---|---|
| `app/routers/movimientos.py` (excluyendo endpoints de reservas y mercados, ver esos módulos) | Listar, crear (individual/múltiple/kit/mercado), exportar Excel, generar/subir PDF, confirmar reserva | `infrastructure/api/routes.py` |
| `app/crud.py::crear_movimiento, get_movimientos, get_movimientos_por_producto, crear_salida_multiple, crear_entrada_multiple, get_movimientos_para_exportar, generar_numero_remision` | Persistencia y reglas de negocio de movimientos | `application/services/*` + `infrastructure/persistence/mongo/movimiento_repository.py` |
| `app/models.py::Movimiento` (la **segunda** definición, líneas ~329–361, que sobreescribe la primera) | Entidad de movimiento | `domain/entities/movimiento.py` |
| `app/schemas.py::MovimientoBase/MovimientoCreate/Movimiento`, `SalidaMultipleCreate`, `EntradaMultipleCreate` | Schemas HTTP | `infrastructure/api/schemas.py` |
| `app/utils/pdf_generator.py` | Generación de comprobantes PDF (salida simple, kit, múltiple, mercado) | `infrastructure/pdf/` (adaptador de un `ComprobantePort`) |

## Responsabilidades detectadas

- Registrar movimiento individual (entrada/salida), actualizando stock total y stock por ubicación.
- Registrar salida/entrada múltiple (varios productos en un solo llamado).
- Confirmar una reserva (`reservas`) como salida real, en 3 modalidades: kit, múltiple, normal — generando remisión y descontando stock reservado y físico.
- Generar número de remisión secuencial (`RM-001`, `RM-002`, ...).
- Generar comprobante PDF de una salida (nueva o ya registrada), y subir un PDF firmado manualmente.
- Exportar movimientos a Excel con filtros de fecha/tipo.
- Registrar "salida por mercado predefinido" (variante que usa `mercados_predefinidos`).

## Domain

- **Entities**: `Movimiento` (producto_id, producto_nombre, tipo [entrada|salida|transferencia_ubicacion|creacion_ubicacion], cantidad, motivo, tipo_origen, origen_nombre, ubicacion, notas, cliente_destino, usuario, usuario_id, fecha_movimiento, pdf_firmado, pdf_nombre, remision, caso, referencia, numero_cajas, es_kit/es_multiple/es_kit_mercado + sus listas de productos anidados).
- **Errors**: producto no encontrado, stock insuficiente (total o por ubicación), ubicación obligatoria para salidas, tipo de movimiento inválido, tipo de origen inválido.

## Application

- **DTO**: `CrearMovimientoDTO`, `CrearSalidaMultipleDTO`, `CrearEntradaMultipleDTO`, `ConfirmarReservaDTO`, `MovimientoDTO`, `FiltroMovimientosDTO`, `SalidaPorMercadoDTO`.
- **Ports**: `MovimientoRepositoryPort`, `GeneradorSecuencialPort` (remisión — candidato shared, ver tabla de candidatos), `ComprobantePort` (generación PDF), y colaboración con los puertos de `productos`, `ubicaciones`, `reservas`, `mercados_predefinidos` desde `application/` (nunca importando sus repositorios concretos).
- **Services** (decisión Fase 0: separados por permiso distinto, no un único
  `RegistrarMovimientoService` genérico): `RegistrarEntradaService`, `RegistrarSalidaService`,
  `RegistrarEntradaMultipleService`, `ConfirmarReservaNormalService`,
  `ConfirmarReservaKitService`, `ConfirmarReservaMultipleService` (dividido en 3, uno por
  modalidad, según la guía de `.claude/CONVENTIONS.md` — resuelve la duda que dejaba abierta
  la versión anterior de este plan), `ListarMovimientosService`, `ExportarMovimientosExcelService`,
  `GenerarComprobantePdfService`, `SubirPdfFirmadoService`, `RegistrarSalidaMultipleService`,
  `RegistrarSalidaPorMercadoService`.

## Infrastructure

- **Persistence**: `MongoMovimientoRepository` (colección **`registro_movimientos`**, aislada
  de la `movimientos` legacy — ver Fase 0), índices ya existentes en legacy (`producto_id`,
  `fecha_movimiento desc`, `tipo`, compuesto `producto_id+fecha_movimiento`) — re-declarar como
  `MongoCollectionDefinition`. Colección **`contadores_movimientos`** (aislada de `contadores`
  legacy) para la remisión.
- **API**: rutas `/api/movimientos` (listar, crear, exportar), `/api/movimientos/entrada-rapida`, `/salida-rapida`, `/salida-multiple`, `/entrada-multiple`, `/generar-pdf-salida`, `/{id}/subir-pdf`, `/salida/{id}/pdf`, `/{id}/pdf-info`, `/salida-por-mercado`, `/comprobante-multiple`, `/reservas/confirmar`, `/reservas/confirmar-multiples`.
- **PDF**: adaptador con `reportlab`.

## Bootstrap

`register_module(app)` registra el router. Debe declararse **después** de `productos`,
`ubicaciones`, `reservas` y `mercados_predefinidos` en el orden de registro si hubiera
dependencias de inicialización (a confirmar en Fase 3; en principio el registro de routers de
FastAPI es independiente del orden).

## Validaciones

- `cantidad > 0`.
- `tipo` en {entrada, salida} (o el conjunto ampliado si se decide modelar transferencia/creación de ubicación como tipos de movimiento propios).
- Para salidas: `ubicacion` obligatoria y con stock físico suficiente.
- Para entradas: `ubicacion` opcional (default `ALMACEN_GENERAL`).

## Riesgos — **el módulo de mayor riesgo de todo el plan**

- **`ConfirmarReservaService` es, en el legacy, una única función de ~250 líneas con 3 ramas casi duplicadas** (kit / múltiple / normal) que además tiene bloques con indentación inconsistente en el archivo original (mezclando espacios, visible en el código fuente) — señal de que este bloque fue parcheado repetidas veces sin refactor. **RESUELTO (Fase 0):** se divide en 3 servicios (`ConfirmarReservaNormalService`/`ConfirmarReservaKitService`/`ConfirmarReservaMultipleService`), construidos en incrementos separados y priorizados por uso real (kit primero, múltiple al final).
- **Transacciones ausentes**: cada rama actualiza `productos`, `ubicaciones`, `movimientos` y `reservas` en llamadas separadas sin Unit of Work — si falla a mitad de camino, el stock queda inconsistente. Es el caso de uso con más razón de negocio para usar `MongoUnitOfWork` desde el día uno. **Nota Fase 0:** esto exigió extender `ReservaRepositoryPort` con `uow` (ver sección Fase 0) — el puerto tal como lo dejó el módulo `reservas` no lo permitía.
- **Detección de ObjectId por heurística**: en varios puntos (`len(str(codigo_producto)) == 24 and str(codigo_producto).isalnum()`) el código intenta adivinar si un valor es un ObjectId de Mongo o un código de producto. Esto es frágil (un código de producto real de 24 caracteres alfanuméricos causaría un falso positivo) y debe reemplazarse por un contrato explícito (el frontend nuevo debe enviar siempre `producto_codigo`, no un identificador ambiguo).
- Los endpoints `/reservas/confirmar` y `/reservas/confirmar-multiples` están **mezclados** dentro de `routers/movimientos.py` pero operan conceptualmente sobre `reservas` + `movimientos` a la vez — es un caso de uso de orquestación entre dos módulos, no de un solo módulo. Se modela aquí (en `movimientos`) porque su efecto final es crear movimientos, pero **debe consumir `reservas` únicamente a través de su puerto público**, nunca su repositorio concreto.
- `confirmar_reservas_multiples` (el endpoint, no el de una sola reserva) está **incompleto en el legacy**: el comentario `# Aquí iría la lógica para actualizar el stock de cada producto ...` indica que nunca se implementó — no actualiza stock real. **RESUELTO (Fase 0):** confirmado con el desarrollador que se incluye igual en el alcance, rediseñado de cero (no hay comportamiento real que preservar), como parte del incremento 6 (baja prioridad, sin uso real hoy).
- `get_ubicaciones_producto` se invoca desde `routers/movimientos.py::salida_por_mercado` pero **no existe ninguna función con ese nombre en `crud.py`** (existe `get_producto_con_ubicaciones`, que retorna una forma distinta). Esto es un bug del legacy — ese endpoint probablemente falla en producción tal como está. **RESUELTO (Fase 0):** verificado contra `inventario_db` real — 0 de 58 movimientos tienen `es_kit_mercado=True`, confirma que este endpoint nunca se usó con éxito. Se incluye igual en el alcance (incremento 6), corrigiendo el bug.
- Dos definiciones de `Movimiento` en `models.py` (la de la línea ~62 queda sombreada por la de la línea ~329) — usar solo la segunda como base de la entidad. **Nota Fase 0:** ninguna de las dos refleja la forma real persistida (ver Hallazgos en Fase 0) — la entidad de dominio se diseña contra los documentos reales, no contra estos modelos Pydantic.
- **Nuevo (Fase 0): `crear_salida_multiple` nunca toca `ubicaciones`** — solo decrementa `productos.stock_actual`, desincronizando `stock_actual` de la suma real de `ubicaciones.stock_fisico` si se usa. No migrar tal cual (incremento 6).
- **Nuevo (Fase 0): `generar_numero_remision` no es atómico** (`find_one` + `update_one` separados) — race condition real bajo concurrencia. Se corrige con `find_one_and_update`/`$inc` en el `GeneradorSecuencialPort` nuevo.
- **Nuevo (incremento 2): doble descuento de `stock_fisico` en la rama "modo normal" de `confirmar_reserva`.** `crud.crear_movimiento(tipo="salida")` ya descuenta `stock_fisico` de la ubicación internamente; el router, justo después, vuelve a descontar la misma ubicación con un `$inc` adicional. Cada confirmación de reserva en modo normal restaba el stock físico dos veces. Corregido: `ConfirmarReservaNormalService` descuenta una sola vez.

## Utilidades reutilizables

- El cálculo de remisión (`generar_numero_remision`) es un patrón de "contador atómico con prefijo" potencialmente reutilizable — ver candidatos a `shared/`.

## Refactorizaciones recomendadas

- Dividir `ConfirmarReservaService` en 3 estrategias (kit / múltiple / normal) con una interfaz común, en vez de una función con 3 ramas `if/elif/else`.
- Introducir `MongoUnitOfWork` en todo servicio que toque más de una colección.
- Sustituir la heurística de "parece un ObjectId" por un contrato explícito de API.

## Código que NO debe migrarse

- `confirmar_reservas_multiples` tal cual (lógica incompleta/no funcional — ver Riesgos).
- La llamada a `crud.get_ubicaciones_producto` (función inexistente) en `salida_por_mercado` — si el endpoint se migra, debe re-implementarse correctamente, no copiarse.
- Los múltiples bloques de `print()` de depuración.

## Incremento 1 — Movimiento individual (completo)

- **Domain**: `Movimiento` + `ItemMovimiento` (value object, sin uso todavía). Campo
  `modalidad` (enum `individual`|`kit`|`multiple`|`entrada_multiple`|`mercado`) nuevo,
  reemplaza los 4 booleans no excluyentes del legacy — aprobado en Fase 1. Dos factories:
  `registrar_entrada()`/`registrar_salida()` (esta última rechaza `ubicacion` vacío). 3
  errores nuevos (`MOV-001`/`002`/`003`).
- **Application**: `MovimientoRepositoryPort`, `GeneradorSecuencialPort` (module-scoped, ver
  Fase 0). `RegistrarEntradaService`/`RegistrarSalidaService` (separados por el permiso
  distinto, no un único servicio genérico), `ListarMovimientosService`,
  `ExportarMovimientosExcelService`. 15 tests nuevos.
- **Infrastructure**: `MongoMovimientoRepository` (colección `registro_movimientos`, aislada),
  `MongoGeneradorSecuencial` (contador atómico vía `find_one_and_update`/`$inc`, colección
  `contadores_movimientos`, aislada), `movimientos_excel_exporter.py` (adaptador
  pandas/openpyxl — no vive en el servicio). 6 tests de infraestructura. Rutas `POST
  /api/movimientos/entradas` (`require_authenticated`), `POST /api/movimientos/salidas`
  (`require_super_admin`), `GET /api/movimientos` (listar paginado con filtros), `GET
  /api/movimientos/exportar/excel`.
- **Higiene**: `pandas`/`openpyxl` (usados por el exportador) no estaban declarados en
  `requirements.txt` — mismo gap ya visto en incrementos anteriores de otros módulos. Corregido.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Usuario de prueba promovido a `super_admin` directamente en Mongo → producto/ubicación de
prueba → entrada individual (stock recalculado como suma de ubicaciones) → entrada sin token
(401) → salida individual (remisión `RM-001`, stock recalculado) → salida con stock
insuficiente (422, `MOV-003`) → salida a ubicación inexistente (404, `MOV-002`) → segunda
salida (`RM-002`, confirma que el contador atómico nuevo — aislado del legacy — no colisiona)
→ listar con filtros combinados (producto + tipo) → listar sin token (401) → exportar Excel
(workbook válido, encabezados y filas correctas). `movimientos`/`contadores` (legacy)
verificados intactos (58 documentos / `ultimo_numero: 23`) antes y después. Datos de prueba
eliminados. `sync_schema --dry-run` y luego aplicado para `registro_movimientos`/
`contadores_movimientos` — ambas creadas vacías con sus índices, sin tocar las colecciones
legacy. Suite completa: **183/183 tests verdes** (162 previos + 21 nuevos).

### Checklist del incremento 1

- [x] Domain — `Movimiento`/`ItemMovimiento`, 3 errores nuevos
- [x] Application — 2 puertos, 4 servicios, 15 tests
- [x] Infrastructure — `MongoMovimientoRepository`, `MongoGeneradorSecuencial`, exportador
  Excel, schemas Mongo (`registro_movimientos`/`contadores_movimientos`), 6 tests
- [x] API — 4 rutas nuevas (permisos diferenciados entrada/salida)
- [x] Bootstrap — `register_module(app)` registrado después de `productos`/`ubicaciones`/
  `mercados_predefinidos`/`reservas`
- [x] `requirements.txt` corregido (`pandas`/`openpyxl`)
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba

## Incremento 2 — Confirmar reserva, modalidad normal (completo)

- **Hallazgo nuevo (releyendo el legacy antes de diseñar)**: doble descuento de `stock_fisico`
  en la rama "modo normal" de `confirmar_reserva` — ver Riesgos. No documentado en la versión
  anterior de este plan porque los incrementos previos no habían entrado a esa rama del
  código legacy en detalle.
- **Domain**: error nuevo `ModalidadReservaNoSoportadaError` (`MOV-004`, 400) — se lanza si la
  reserva resulta ser modalidad `kit`/`multiple` (detectadas con la misma heurística del
  legacy: `datos_adicionales.tipo`, o `kitNombre` como señal de kit sin `tipo` explícito).
- **Cambio en un módulo ya cerrado**: `ReservaRepositoryPort.actualizar`/`eliminar` (módulo
  `reservas`) ahora aceptan `uow: UnitOfWorkPort | None = None` — mismo patrón que
  `UbicacionRepositoryPort`/`ProductoRepositoryPort`. Cambio aislado y retrocompatible (los
  call-sites existentes de `AjustarReservaService`/`EliminarReservaService` no pasan `uow` y
  siguen funcionando igual — verificado, sin regresiones en la suite de `reservas`).
- **Application**: `ConfirmarReservaNormalService` (en `modules/movimientos/`, consume
  `ReservaRepositoryPort` solo por puerto). Genera **una remisión compartida** por todos los
  items de la reserva, descuenta stock por ubicación **una sola vez**, recalcula
  `stock_actual`, crea un `Movimiento` por item, y borra la reserva — todo dentro de un único
  `MongoUnitOfWork` (si un item falla a mitad de camino, la transacción completa hace
  rollback: ningún item queda aplicado a medias, la reserva no se borra). 11 tests nuevos del
  servicio + 4 tests de infraestructura (`MongoReservaRepository`, propagación de sesión).
- **Infrastructure**: ruta `POST /api/movimientos/reservas/{session_id}/confirmar`
  (`require_super_admin`, ya decidido). Sin body — `cliente_destino`/`notas` vienen de
  `reserva.datos_adicionales`.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Usuario de prueba promovido a `super_admin` → producto/ubicación de prueba (stock 100) →
armar reserva vía `/api/reservas/{session_id}/ajustar` (+15) → confirmar sin token (401) →
confirmar con rol `operativo` (403) → confirmar sesión inexistente (404, `RES-002`) →
confirmar una reserva modalidad kit (400, `MOV-004`, sin tocar stock) → confirmar la reserva
real (201, un movimiento, remisión `RM-001`, `cliente_destino`/`motivo` correctos) → **stock
descontado una sola vez** (100 − 15 = 85, no 70 — confirma la corrección del bug de doble
descuento) → reserva eliminada tras confirmar (404 al reconsultarla) → confirmar de nuevo la
misma sesión (404, ya no existe). `movimientos`/`contadores`/`reservas` (legacy) verificados
intactos (58 documentos / `RM-023` / 3 reservas) antes y después. Datos de prueba eliminados.
Suite completa: **198/198 tests verdes** (183 previos + 15 nuevos).

### Checklist del incremento 2

- [x] Domain — 1 error nuevo (`MOV-004`)
- [x] Application — extensión de `ReservaRepositoryPort` (uow), `ConfirmarReservaNormalService`,
  11 tests
- [x] Infrastructure — extensión de `MongoReservaRepository`, 4 tests, 1 ruta nueva
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba; sin regresiones en la suite de `reservas`

## Incremento 3 — Confirmar reserva modalidad kit + comprobante PDF (completo)

- **Hallazgo nuevo (releyendo la rama kit antes de diseñar)**: el legacy trackea
  `numero_cajas` por item de reserva (`item.get('cajas')`), pero el `ItemReserva` del módulo
  `reservas` (ya cerrado) no tiene ese campo, y ningún kit real en `inventario_db` lo tenía
  poblado tampoco. **Decisión:** `numero_cajas` queda en `0` para kits — no se reabre
  `reservas` para un campo que nunca se usó en la práctica.
- **Refactor de despacho por modalidad** (afecta el incremento 2, ya cerrado): con dos de las
  tres estrategias existiendo, se separó la responsabilidad — `ConfirmarReservaService`
  (dispatcher nuevo) lee la reserva **una sola vez**, detecta la modalidad, y delega a
  `ConfirmarReservaNormalService`/`ConfirmarReservaKitService`, que ahora reciben la `Reserva`
  ya resuelta (no el `session_id`) y ya no repiten la detección de modalidad. Implementa la
  "interfaz común" que esta sección del plan sugería desde el análisis original. Los tests
  del incremento 2 se reescribieron para la firma nueva (11 tests, mismo conteo).
- **Domain**: `Movimiento.registrar_kit()` (una sola salida por kit, `cantidad=1` fijo,
  `productos` embebidos, `numero_cajas=0`), `Movimiento.adjuntar_pdf_firmado()`. 3 errores
  nuevos: `MOV-005` (movimiento no encontrado), `MOV-006` (archivo no es PDF), `MOV-007` (sin
  PDF firmado subido todavía).
- **Application**: `ConfirmarReservaKitService`, `GenerarComprobantePdfService`,
  `SubirPdfFirmadoService`, `ObtenerPdfFirmadoService`. `MovimientoRepositoryPort` ampliado
  con `obtener_por_id`/`actualizar`. Puertos nuevos `ComprobantePort` y
  `StorageRepositoryPort` (ambos module-scoped, ver Fase 0). 34 tests nuevos.
- **Infrastructure**: `ReportlabComprobanteAdapter` (mismo formato visual que el legacy,
  reescrito para leer de `Movimiento`; solo cubre individual/kit, no mercado/múltiple).
  `DiskStorageRepository` (nueva colección de infraestructura — primera vez que el proyecto
  guarda archivos; setting `STORAGE_DIR`, default `storage/` en la raíz, con sanitización de
  nombre de archivo contra path traversal). **Sin servir estáticos** (decisión ya tomada): el
  PDF firmado se descarga vía `GET /{id}/pdf-firmado`, no una URL estática. Rutas nuevas: `GET
  /{id}/comprobante`, `POST /{id}/pdf-firmado`, `GET /{id}/pdf-firmado`. 10 tests de
  infraestructura (repositorio Mongo, storage en disco con `tmp_path`, smoke test del PDF).
- **Higiene**: `reportlab` y `python-multipart` (ya instalados, usados desde este incremento)
  no estaban declarados en `requirements.txt` — mismo gap ya visto en incrementos anteriores.
  Corregido. `.gitignore` actualizado (`/storage/`) para no versionar archivos subidos.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Dos productos/ubicaciones de prueba (stock 50 cada uno) → armar reserva kit (5 + 2 unidades,
`kitNombre`/`cliente`/`caso`) → confirmar (201, **un solo** movimiento modalidad kit,
`cantidad=1`, `numero_cajas=0`, 2 productos embebidos, remisión `RM-001`) → stock descontado
correctamente en ambas ubicaciones (45 y 48) → reserva eliminada → **regresión**: confirmar
una reserva modalidad normal después del refactor del dispatcher sigue funcionando (`RM-002`)
→ generar comprobante del kit (200, PDF válido) → comprobante de movimiento inexistente (404,
`MOV-005`) → subir PDF firmado (200, `pdf_nombre` actualizado) → subir archivo no-PDF (400,
`MOV-006`) → descargar el PDF firmado (200, bytes idénticos a lo subido) → descargar PDF de un
movimiento sin PDF subido (404, `MOV-007`). `movimientos`/`contadores` (legacy) verificados
intactos (58 documentos / `RM-023`). Datos de prueba y carpeta `storage/` de prueba eliminados.
Suite completa: **228/228 tests verdes**.

### Checklist del incremento 3

- [x] Domain — `registrar_kit`/`adjuntar_pdf_firmado`, 3 errores nuevos
- [x] Application — refactor del dispatcher (afecta incremento 2), `ConfirmarReservaKitService`,
  3 servicios de PDF, 2 puertos nuevos, `MovimientoRepositoryPort` ampliado, 34 tests
- [x] Infrastructure — `ReportlabComprobanteAdapter`, `DiskStorageRepository`, setting
  `STORAGE_DIR`, 3 rutas nuevas, 10 tests
- [x] `requirements.txt`/`.gitignore` corregidos
- [x] Verificación end-to-end completa (incluye regresión de modalidad normal) contra
  `inventario_db` real, con limpieza de datos de prueba

## Incremento 4 — Entrada múltiple directa (completo)

- **Hallazgo nuevo (releyendo `crear_entrada_multiple` antes de diseñar)**: bug real de
  integridad de datos. El legacy resuelve la ubicación real donde aplica el stock como
  `item.get('ubicacion') or ubicacion or 'ALMACEN_GENERAL'` (línea 466 de `crud.py`), pero
  guarda en el item persistido `item.get('ubicacion', 'ALMACEN_GENERAL')` (línea 474) — **sin
  considerar el `ubicacion` global del request**. Si un item no trae su propia ubicación pero
  el request sí trae una global, el stock se aplica ahí, pero el documento persistido muestra
  `"ALMACEN_GENERAL"` — una ubicación que puede no tener ese stock en absoluto. No se
  reprodujo: el item persistido siempre refleja la ubicación real usada.
- **Domain**: `Movimiento.registrar_entrada_multiple()` — una sola entrada, `cantidad` = suma
  de items, `motivo = tipo_origen.capitalize()` (igual que el legacy), `productos` embebidos
  con la ubicación ya resuelta (corrige el bug de arriba). Error nuevo `MOV-008` (sin
  productos — invariante de dominio, además de la validación `Field(min_length=1)` en el DTO).
- **Application**: `RegistrarEntradaMultipleService` (mismo patrón por-item que
  `RegistrarEntradaService`/`ConfirmarReservaKitService`: resuelve ubicación, suma stock,
  recalcula `stock_actual`, todo en una transacción). `RegistrarEntradaMultipleInput` valida
  `tipo_origen` contra el mismo vocabulario fijo del legacy (`compra`/`donacion`/
  `devolucion`/`traslado`/`ajuste`, normalizado a minúsculas) — a diferencia de la entrada
  individual, donde `tipo_origen` es texto libre (así era también en el legacy: solo
  `EntradaMultipleCreate` validaba el vocabulario). La misma validación se duplica en el
  schema HTTP (`RegistrarEntradaMultipleRequest`) para que FastAPI la resuelva como 422 en el
  borde de la API, no como un 500 al construir el DTO interno. 12 tests nuevos (9 del servicio
  + 3 del DTO).
- **Infrastructure**: ruta `POST /api/movimientos/entradas/multiple`, `require_authenticated`
  (mismo criterio que la entrada individual — solo la salida directa y la confirmación de
  reserva son exclusivas de `super_admin`).

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Dos productos de prueba → entrada múltiple con un item con ubicación propia y otro sin
ubicación (usa la global del request) → 201, un solo movimiento modalidad `entrada_multiple`,
`cantidad=15`, `motivo="Compra"` (capitalizado desde `tipo_origen` normalizado), 2 items
embebidos → **el item sin ubicación propia registra la ubicación global real**
(`TEST-GLOBAL-4`), no un `"ALMACEN_GENERAL"` falso → stock recalculado correctamente en ambos
productos → la ubicación global se creó de verdad con el stock correcto → `tipo_origen`
inválido (422) → `productos` vacío (422) → producto inexistente (404, `PROD-002`) → sin token
(401). `movimientos`/`contadores` (legacy) verificados intactos (58 documentos / `RM-023`).
Datos de prueba eliminados. Suite completa: **240/240 tests verdes**.

### Checklist del incremento 4

- [x] Domain — `registrar_entrada_multiple`, error `MOV-008`
- [x] Application — `RegistrarEntradaMultipleService`, DTO con validación de `tipo_origen`,
  12 tests
- [x] Infrastructure — 1 ruta nueva (`require_authenticated`)
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba

## Incremento 5 — Bitácora de `ubicaciones` en `movimientos` (completo)

Reabre el módulo `ubicaciones` (ya cerrado) para que `CrearUbicacionService`/
`TransferirStockService` dejen constancia en `registro_movimientos` — decisión y patrón ya
acordados en la Fase 0 general de `movimientos` (inversión de dependencias, para no crear el
ciclo `movimientos↔ubicaciones`).

- **Puerto nuevo, propiedad de `ubicaciones`**: `RegistradorDeMovimientosPort`
  (`modules/ubicaciones/application/ports/`) con `registrar_creacion_ubicacion`/
  `registrar_transferencia_stock` — ambos con `uow` opcional, para participar de la misma
  transacción que el cambio de stock. `ubicaciones/application` no importa nada de
  `movimientos` en ningún momento.
- **Domain (`movimientos`)**: `Movimiento.registrar_creacion_ubicacion()`/
  `registrar_transferencia_ubicacion()` — registros puramente históricos, no alteran stock
  (eso ya lo hizo `ubicaciones`).
- **Adaptador concreto, propiedad de `movimientos`**:
  `MovimientosRegistradorDeMovimientosAdapter` (`modules/movimientos/infrastructure/ubicaciones/`)
  — implementa el puerto de `ubicaciones`, resuelve `producto_nombre` vía su propio
  `ProductoRepositoryPort` (así `ubicaciones` no necesita pasarlo). Cableado únicamente en
  `modules/ubicaciones/infrastructure/api/dependencies.py`, que importa el *provider* de
  dependencia desde `modules/movimientos/infrastructure/api/dependencies.py` — mismo patrón
  ya usado para wire-in de `productos` en `ubicaciones` (no es una excepción nueva al patrón
  de composición del proyecto).
- **Alcance**: solo `CrearUbicacionService` y `TransferirStockService` (los dos tipos que
  aparecen en los datos reales: `creacion_ubicacion`/`transferencia_ubicacion`).
  `ActualizarUbicacionService`/`EliminarUbicacionService` quedan fuera — sin precedente real.
- **3 bugs nuevos encontrados y corregidos durante la verificación end-to-end** (no durante el
  diseño — solo aparecieron al ejercitar el endpoint real por primera vez con estos tipos):
  1. `ListarMovimientosInput.tipo`/`ExportarMovimientosExcelInput.tipo` estaban tipados como
     `Literal["entrada", "salida"]` — filtrar por `tipo=creacion_ubicacion` u otro valor
     nuevo lanzaba un 500 (`ValidationError` sin capturar) en vez de devolver resultados.
     Ampliados a los 4 valores de `TipoMovimiento`.
  2. El exportador de Excel etiquetaba cualquier `tipo` distinto de `"entrada"` como
     `"SALIDA"` — una bitácora de ubicación se habría mostrado como salida de inventario en
     el reporte. Corregido con un mapeo explícito por tipo.
  3. `MovimientoResponse` no exponía `ubicacion_origen`/`ubicacion_destino` — los únicos
     campos que identifican una transferencia quedaban invisibles vía API. Agregados a la
     respuesta.
- **Tests**: 15 nuevos — 2 de dominio (las 2 factories nuevas), 2 de bitácora en los
  servicios reabiertos de `ubicaciones`, 3 del adaptador nuevo, 5 del DTO `tipo` ampliado
  (4 valores válidos + 1 rechazo), 3 del exportador Excel (etiquetas nuevas).

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Producto de prueba → crear ubicación (stock 50) → **queda una bitácora `creacion_ubicacion`**
con `producto_codigo`/`producto_nombre`/`ubicacion`/`cantidad` correctos → exportar Excel
filtrado por `tipo=creacion_ubicacion` con la etiqueta correcta (no `"SALIDA"`) → crear
segunda ubicación → transferir 15 unidades → **queda una bitácora `transferencia_ubicacion`**
con `ubicacion_origen`/`ubicacion_destino` correctos y expuestos en la respuesta → stock real
verificado en ambas ubicaciones (35/15). `movimientos`/`ubicaciones` (legacy) verificados
intactos (58 documentos / 12 ubicaciones) antes y después. Datos de prueba eliminados. Suite
completa: **255/255 tests verdes**.

### Checklist del incremento 5

- [x] Domain (`movimientos`) — 2 factories nuevas de bitácora
- [x] Application (`ubicaciones`) — `RegistradorDeMovimientosPort` nuevo; `CrearUbicacionService`/
  `TransferirStockService` reabiertos para consumirlo
- [x] Infrastructure (`movimientos`) — `MovimientosRegistradorDeMovimientosAdapter`; wiring
  cruzado en `ubicaciones/infrastructure/api/dependencies.py`
- [x] 3 bugs de integración corregidos (`tipo` restringido en 2 DTOs, etiqueta Excel,
  `ubicacion_origen`/`destino` no expuestos) — todos detectados en la verificación end-to-end
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba; sin regresiones en la suite de `ubicaciones`

## Incremento 6 — Múltiple/mercado directos + confirmar reserva múltiple (completo) — **módulo `movimientos` cerrado**

Última pieza del alcance de la Fase 0: las tres modalidades sin uso real en `inventario_db`
(0/58 movimientos) — confirmar reserva múltiple, salida múltiple directa, salida por mercado —
todas rediseñadas respecto al legacy, con sign-off explícito del desarrollador antes de
construir (3 desviaciones deliberadas, ver abajo).

- **Domain**: `Movimiento.registrar_multiple()` (cantidad fija en 1, `numero_cajas=0`, sin
  `kit_nombre`) y `Movimiento.registrar_mercado()` (multiplica cada `ProductoKit.cantidad` por
  la cantidad de mercados solicitada, guarda `nombre_mercado`/`referencia`). `MovimientoSinProductosError`
  (`MOV-008`) generalizado — antes solo hablaba de "entrada múltiple", ahora la comparten
  `registrar_entrada_multiple`, `registrar_multiple` y `registrar_mercado`.
- **Application — 3 servicios nuevos**:
  1. `ConfirmarReservaMultipleService` — misma forma que `ConfirmarReservaKitService`, motivo
     fijo `"Entrega de Ayudas/Unidades"` (igual que el legacy). El dispatcher
     `ConfirmarReservaService` ahora resuelve 3 modalidades (`normal`/`kit`/`multiple`) en vez de
     2; `ModalidadReservaNoSoportadaError` queda solo para modalidades realmente desconocidas.
  2. `RegistrarSalidaMultipleService` — una sola salida con N productos, **cada uno con su
     propia ubicación** (a diferencia de la entrada múltiple, que sí acepta una ubicación
     global de fallback).
  3. `RegistrarSalidaPorMercadoService` — consume `MercadoPredefinidoRepositoryPort` (solo
     lectura) para resolver los productos del kit predefinido.
- **3 desviaciones deliberadas del comportamiento legacy** (aprobadas explícitamente antes de
  construir, no asumidas):
  1. Un único `Movimiento` embebido (con `productos: list[ItemMovimiento]`) en vez de N
     movimientos separados — mismo patrón ya usado por `kit`/`multiple`.
  2. `RegistrarSalidaPorMercadoService` exige **una ubicación explícita** para todos los
     productos del mercado — el legacy intentaba auto-elegir una ubicación con stock
     suficiente llamando a `crud.get_ubicaciones_producto`, función que **no existe** en el
     código legacy real (bug nunca ejecutado en producción). No se reconstruye ese heurístico.
  3. El comprobante PDF se genera on-demand vía el endpoint ya existente
     (`GET /{movimiento_id}/comprobante`), no automáticamente al registrar la salida.
  4. **Fuera de alcance, documentado como deuda futura**: "confirmar varias reservas en un
     comprobante" — el legacy nunca lo implementó, no hay comportamiento real que preservar.
     Se diseña de cero si en algún momento hay demanda real.
- **Infrastructure**: `ReportlabComprobanteAdapter` generalizado — el flag interno pasó de
  `es_kit` a `es_multi_producto` (`{"kit", "multiple", "mercado"}`), agrega líneas
  `MERCADO PREDEFINIDO:`/`REFERENCIA:` cuando corresponde, y el título de la tabla usa
  `kit_nombre` o `nombre_mercado` indistintamente (`"PRODUCTOS DE: {nombre}"`).
- **Rutas nuevas** (`require_super_admin`, igual que toda creación de salida real):
  `POST /api/movimientos/salidas/multiple`, `POST /api/movimientos/salida-por-mercado`. El
  docstring de `POST /reservas/{session_id}/confirmar` se actualizó — "múltiple" ya no es una
  modalidad rechazada.
- **Tests**: 25 nuevos (domain, DTOs, los 3 servicios de aplicación, adaptador PDF con los 2
  nuevos casos) — 280/280 en la suite completa.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

Dos productos + dos ubicaciones propias → `POST /salidas/multiple` con un item por ubicación →
**un solo movimiento** modalidad `multiple` con remisión propia, stock descontado
independientemente en cada ubicación (no hay descuento cruzado), comprobante PDF descargable,
stock insuficiente → 422. Mercado predefinido con 2 productos → ambos productos deben existir
en la **misma** ubicación explícita (comportamiento intencional, distinto del legacy) →
`POST /salida-por-mercado` → un solo movimiento modalidad `mercado` con cantidades multiplicadas
correctamente, `nombre_mercado`/`referencia` expuestos, comprobante descargable, mercado
inexistente → 404 `MERC-002`. Reserva con `datos_adicionales.tipo="multiple"` y 2 items →
confirmar → un solo movimiento con motivo fijo, stock descontado una sola vez, reserva
eliminada tras confirmar. Los tres flujos verificados también contra `require_super_admin`
(403 para rol `operativo`). `movimientos` (58) y `mercados_predefinidos` (7, colección legacy
separada de `catalogo_mercados_predefinidos`) verificados intactos antes y después. Datos de
prueba eliminados. Suite completa: **280/280 tests verdes**.

### Checklist del incremento 6

- [x] Domain — `registrar_multiple`/`registrar_mercado`, error `MOV-008` generalizado
- [x] Application — 3 servicios nuevos (`ConfirmarReservaMultipleService`,
  `RegistrarSalidaMultipleService`, `RegistrarSalidaPorMercadoService`), dispatcher actualizado
- [x] Infrastructure — adaptador PDF generalizado a multi-producto, 2 rutas nuevas
  (`require_super_admin`), wiring de dependencias (incluye `MercadoPredefinidoRepositoryPort`
  como dependencia de solo lectura)
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba; sin regresiones en la suite completa (280/280)
- [x] Deuda documentada: "confirmar varias reservas en un comprobante" queda sin construir,
  sin demanda real que lo justifique hoy

## Módulo `movimientos` — CERRADO (6/6 incrementos completos)

Los 6 incrementos acordados en la Fase 0 quedaron completos: núcleo (entrada/salida
individual), confirmar reserva normal, confirmar reserva kit + comprobante PDF, entrada
múltiple directa, bitácora de `ubicaciones`, y confirmar reserva múltiple + salida
múltiple/mercado directas. 280 tests unitarios en la suite completa del proyecto, verificación
end-to-end de cada incremento contra `inventario_db` real (colecciones aisladas
`registro_movimientos`/`contadores_movimientos`), sin ningún impacto sobre las colecciones
legacy (`movimientos`, `contadores`, `ubicaciones`, `mercados_predefinidos`) en ningún momento.
Colabora con `productos`, `ubicaciones`, `reservas` y `mercados_predefinidos` exclusivamente vía
puertos (nunca repositorios concretos), usando `MongoUnitOfWork` en toda operación
multi-colección. La bitácora de `ubicaciones` (incremento 5) resolvió la única dependencia
inversa del plan mediante inversión de dependencias (`RegistradorDeMovimientosPort` propiedad
de `ubicaciones`, adaptador concreto en `movimientos`), sin introducir ningún ciclo entre
módulos.

**Deuda documentada, sin construir** (sin demanda real hoy): "confirmar varias reservas en un
comprobante". Fuera de eso, el alcance acordado en la Fase 0 está completo.

**Reapertura posterior** (durante la Fase 0 de `aprobaciones_pendientes`, ver esa sección):
los 4 servicios de registro directo (`RegistrarEntradaService`, `RegistrarEntradaMultipleService`,
`RegistrarSalidaService`, `RegistrarSalidaMultipleService`) ganaron un parámetro `uow` opcional
en `ejecutar()`, y se agregó `EjecutorDeMovimientosPort` (propiedad de `movimientos`) para que
`aprobaciones_pendientes` pueda aplicar el movimiento real y actualizar su propia propuesta en
una única transacción. No disruptivo — ningún llamador previo pasa `uow`, comportamiento
existente sin cambios.

**Siguiente módulo según la prioridad de migración** (al momento de cerrar este módulo): ver
"Prioridad de migración" al inicio de este documento — `aprobaciones_pendientes` e
`inventario_reportes` quedaban pendientes de definición de negocio antes de poder migrarse.
Ambos ya están cerrados (ver sus propias secciones) — la migración completa terminó con
`inventario_reportes`.

## Observaciones

**Actualizado en Fase 0** (reemplaza la recomendación genérica anterior): el orden de
incrementos se decidió por **uso real verificado contra `inventario_db`** (23/58 confirmaciones
kit, 3/58 entrada múltiple, 0/58 múltiple y mercado), no por la intuición del plan original. Ver
"Plan de incrementos" en la sección Fase 0 para el detalle completo de los 6 incrementos y sus
decisiones asociadas (permisos, nombres de colección, extensión de `ReservaRepositoryPort`,
bitácora de `ubicaciones` con inversión de dependencias).

---

# Módulo `aprobaciones_pendientes` — CERRADO (1/1 incremento completo)

## Objetivo

Permitir que usuarios no administradores propongan una entrada o salida de inventario que
queda pendiente hasta que un `super_admin` la apruebe (o la elimine), momento en el cual se
genera el movimiento real correspondiente.

## Archivos legacy involucrados

| Archivo origen | Responsabilidad detectada | Destino real |
|---|---|---|
| `app/routers/movimientos.py::guardar_entrada_pendiente, obtener_entradas_pendientes, eliminar_entrada_pendiente, eliminar_entradas_pendientes_multiples, confirmar_entradas_pendientes` | Flujo de entradas pendientes | `modules/aprobaciones_pendientes/infrastructure/api/routes.py` |
| `app/routers/movimientos.py::guardar_salida_pendiente, obtener_salidas_pendientes, eliminar_salida_pendiente, eliminar_salidas_pendientes_multiples, confirmar_salidas_pendientes` | Flujo de salidas pendientes | ídem — unificado con entradas |

## Fase 0 — Alcance acordado (WORKFLOW.md)

### Hallazgos confirmados contra el código legacy real (no solo el resumen del plan)

Lectura completa de `routers/movimientos.py` confirmó lo que el plan original solo sospechaba:

- **No existe ningún modelo Pydantic** para "entrada/salida pendiente" — los endpoints reciben
  `dict` genérico sin validación estructurada; el único tipado real es
  `confirmar_entradas_pendientes(entradas_ids: List[str], ...)`.
- **`crud.py` no tiene ninguna función relacionada** — toda la manipulación de
  `entradas_pendientes`/`salidas_pendientes` ocurre directamente en el router.
- **"Confirmar" es un stub que nunca aplicó el movimiento real**: en ambas funciones
  (`confirmar_entradas_pendientes`/`confirmar_salidas_pendientes`) la variable `datos` se lee
  pero nunca se usa; las líneas `# Llamar a tu función de entrada múltiple` /
  `# await crud.crear_entrada_multiple(db, ...)` están comentadas y jamás se ejecutaron. El
  endpoint solo hacía `update_one({"estado": "confirmada"})` — sin tocar stock, ubicaciones ni
  crear un documento en `movimientos`.
- **Sin índices Mongo** en ninguna de las dos colecciones legacy.
- **Matriz de permisos real**: guardar → cualquier autenticado; listar → `super_admin` ve
  todas, el resto solo las propias (filtro por `usuario_id`); eliminar individual → dueño o
  `super_admin`; eliminar en lote y confirmar → solo `super_admin`. `admin` no tiene privilegio
  especial (se trata igual que `operativo`).
- Es un flujo **distinto y desconectado** de `reservas` (ya migrado y funcional) — `reservas`
  es un carrito de sesión con confirmación real; esto es una cola de propuestas de cualquier
  usuario que nunca llegó a aplicarse de verdad.

### Decisiones cerradas con el desarrollador

| Pregunta | Decisión |
|---|---|
| ¿Qué debe hacer "confirmar" realmente? | **Aplicar el movimiento real** — invoca el servicio real de `movimientos` correspondiente según el tipo propuesto (`RegistrarEntradaService`/`RegistrarEntradaMultipleService`/`RegistrarSalidaService`/`RegistrarSalidaMultipleService`). Corrige el bug/stub del legacy, no lo reproduce. |
| ¿Quién puede aprobar salidas pendientes o confirmar entradas pendientes? | **Exclusivamente `super_admin`** — ningún otro rol, ni siquiera `admin`. El operativo (o cualquier no-super_admin) solo puede dejar la propuesta en estado "pre" (`pendiente`) — no puede aprobarla. Confirmado explícitamente por el desarrollador. |
| ¿Qué usuario queda como autor (`creado_por`) del `Movimiento` generado al confirmar? | **El `super_admin` que confirma** — es quien ejecuta la acción real que mueve stock, no quien la propuso. |
| ¿Unificar `EntradaPendiente`/`SalidaPendiente`? | **Sí** — una sola entidad `MovimientoPendiente` con discriminador `tipo_propuesto`, dado que la lógica de autorización y ciclo de vida es idéntica en el legacy. |
| Atomicidad entre "crear el movimiento real" y "marcar la pendiente como confirmada" | Los 4 servicios de `movimientos` (`RegistrarEntradaService`, etc.) abrían su propia transacción interna, sin aceptar un `uow` externo — riesgo real de duplicado si el segundo paso fallara después de que el primero ya tuvo éxito. **Se reabre `movimientos`** para agregarles un parámetro `uow` opcional en `ejecutar()`, de modo que `ConfirmarMovimientoPendienteService` cubra ambos pasos con una única transacción. No disruptivo — ningún llamador existente lo pasa. |
| Operaciones proponibles | `entrada`, `entrada_multiple`, `salida`, `salida_multiple` — mapeadas 1 a 1 a los 4 servicios de `movimientos`. Fuera de alcance: `salida_por_mercado` (sin precedente en el flujo legacy de pendientes) y confirmar reservas (ya tiene su propio mecanismo, sin relación con este módulo). |
| Nombre de colección | **`movimientos_pendientes`** (nueva, aislada) — no colisiona con las legacy `entradas_pendientes`/`salidas_pendientes` (confirmadas existentes y con datos reales, verificado por `listCollections` antes de crear la nueva). |

## Fase 1 — Modelado MongoDB (colección `movimientos_pendientes`) — **APROBADA**

```json
{
  "_id": ObjectId,
  "tipo_propuesto": "entrada" | "entrada_multiple" | "salida" | "salida_multiple",
  "payload": { /* forma validada en la capa de aplicación según tipo_propuesto */ },
  "estado": "pendiente" | "confirmada",
  "movimiento_id": ObjectId | null,
  "creado_por": { "id_persona": ObjectId, "nombre": "string", "fecha": "date" },
  "confirmado_por": { "id_persona": ObjectId, "nombre": "string", "fecha": "date" } | null
}
```

- `payload` se embebe (objeto fijo, sin array que crezca); a nivel de esquema Mongo queda
  como `object` sin validación profunda — mismo criterio que `reservas.datos_adicionales`.
- `movimiento_id` es referencia pura (solo el id), completada al confirmar.
- Sin historial de estados embebido: solo hay una transición posible
  (`pendiente → confirmada`) y `confirmado_por` ya lleva la fecha de esa transición.
- Índices: `estado`, compuesto `(creado_por.id_persona, estado)` (el caso más común: "mis
  propuestas sin confirmar"), `tipo_propuesto`, `creado_por.fecha` desc.

## Fase 2 — Domain + Application — **APROBADA**

- **Domain**: `MovimientoPendiente.proponer()`/`.confirmar()` (lanza
  `MovimientoPendienteYaConfirmadoError` si ya no está `pendiente`)/`.exigir_eliminable()`/
  `.pertenece_a(id_persona)` — pura comparación de identidad, sin conocer roles (eso es
  responsabilidad de la capa de aplicación).
- **Puerto nuevo, propiedad de `movimientos`**: `EjecutorDeMovimientosPort`
  (`modules/movimientos/application/ports/`), consumido por `aprobaciones_pendientes` —
  envuelve los 4 servicios de `movimientos` con `uow` ya expuesto. Adaptador concreto
  (`MovimientosEjecutorAdapter`) en `modules/movimientos/infrastructure/aprobaciones/`. Mismo
  patrón de cableado cruzado que `RegistradorDeMovimientosPort` (incremento 5 de
  `movimientos`), pero sin necesidad de inversión de dependencias — no hay ciclo, porque
  `movimientos` nunca necesita llamar de vuelta a `aprobaciones_pendientes`.
- **Servicios**: `ProponerEntradaService`/`ProponerEntradaMultipleService`/
  `ProponerSalidaService`/`ProponerSalidaMultipleService` (reutilizan directamente los
  `Input` DTO de `movimientos`, sin duplicar su validación), `ListarMovimientosPendientesService`
  (fuerza el filtro de dueño según el rol, nunca confía en lo que traiga el request),
  `EliminarMovimientoPendienteService`, `EliminarMovimientosPendientesMultiplesService`
  (solo `super_admin`, best-effort, no elimina ya confirmadas), `ConfirmarMovimientoPendienteService`
  (dispatcher: reconstruye el `Input` real desde `payload` según `tipo_propuesto`, todo dentro
  de una única transacción).
- **Errores** (`APR-xxx`): `MovimientoPendienteNoEncontradoError` (404),
  `MovimientoPendienteYaConfirmadoError` (409, también al intentar eliminar una ya confirmada),
  `PendienteNoPerteneceAlUsuarioError` (403).

## Fase 3 — Construcción (completa)

- **Reapertura de `movimientos`**: los 4 servicios de registro directo ganaron un parámetro
  `uow: UnitOfWorkPort | None = None` en `ejecutar()` — extraído a un método privado
  `_registrar(...)` que recibe el `uow` ya resuelto (propio o externo). 4 tests nuevos de
  regresión (uno por servicio) verificando que con un `uow` externo no se abre una transacción
  propia.
- **Rutas** (`/api/aprobaciones-pendientes`): `POST /entradas`, `/entradas/multiple`,
  `/salidas`, `/salidas/multiple` (proponer, `require_authenticated`); `GET ""` (listar,
  `require_authenticated`); `DELETE /{id}` (eliminar individual, `require_authenticated` +
  chequeo de dueño en el servicio); `DELETE /eliminar-multiples` (`require_super_admin`);
  `POST /{id}/confirmar` (`require_super_admin`, responde con el `MovimientoResponse` real de
  `movimientos`).
- **Tests**: 40 nuevos — 8 en la suite de `movimientos` (4 de regresión del `uow` opcional + 4
  del adaptador `MovimientosEjecutorAdapter`) y 32 en `aprobaciones_pendientes` (6 de dominio,
  19 de aplicación, 7 de repositorio Mongo con mocks) — 320/320 en la suite completa.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

`super_admin` + 2 operativos + 2 productos/ubicaciones de prueba → cada operativo propone
entrada/salida/entrada_multiple/salida_multiple → **listar como operativo solo muestra las
propias, listar como super_admin muestra las de todos** → confirmar con operativo (403) →
confirmar entrada con super_admin (201, `Movimiento` real creado, stock recalculado
correctamente, `pendiente.movimiento_id` completado) → confirmar de nuevo la misma (409,
`APR-002`) → confirmar `salida_multiple` (201, cubre el otro extremo del dispatcher, stock
descontado correctamente) → confirmar inexistente (404, `APR-001`) → eliminar la propuesta de
otro usuario sin ser super_admin (403, `APR-003`) → el dueño elimina la propia (204) → eliminar
una ya confirmada (409, `APR-002`) → eliminar inexistente (404, `APR-001`) →
`eliminar-multiples` con operativo (403), con super_admin sobre una mezcla de
pendiente/confirmada/inexistente (200, solo elimina la pendiente real:
`{"eliminadas": 1, "total_solicitadas": 3}`). Colecciones legacy `movimientos`,
`entradas_pendientes` y `salidas_pendientes` verificadas intactas antes y después (la
colección `movimientos_pendientes`, nueva, nunca las toca). Datos de prueba eliminados. Suite
completa: **320/320 tests verdes**.

### Checklist de migración

- [x] Domain — `MovimientoPendiente` unificada + 3 errores `APR-xxx`
- [x] Application — `EjecutorDeMovimientosPort` (propiedad de `movimientos`) + 8 servicios
- [x] Infrastructure — colección `movimientos_pendientes` (schema + índices aplicados), 8
  rutas HTTP, wiring cruzado con `movimientos`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 40 nuevos, 320/320 en la suite completa
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos de
  prueba; legacy `movimientos`/`entradas_pendientes`/`salidas_pendientes` intactos

## Observaciones

A diferencia del resto del plan, este módulo **no migra una capacidad funcional del legacy en
su parte central** (confirmar nunca funcionó ahí) — es, de facto, la primera implementación
real de esa capacidad, diseñada desde una Fase 0 explícita con el desarrollador en vez de
asumida a partir del código legacy roto. El resto del flujo (guardar/listar/eliminar) sí
preserva la forma y las reglas de autorización del legacy.

**Módulo cerrado**: `inventario_reportes` era el único que quedaba del plan original — ver su
propia sección para el cierre completo.

---

# Módulo `inventario_reportes` — CERRADO (último módulo del plan)

## Objetivo

Exponer vistas agregadas de solo lectura sobre el inventario: estadísticas de dashboard,
productos bajo stock mínimo, valor total del inventario y reporte consolidado. No introduce
entidades ni colección propia — puro composición de lectura sobre `productos` y
`movimientos`, consumidos exclusivamente por puerto.

## Fase 0 — Alcance acordado

### Hallazgos confirmados contra el código legacy real

Verificación exhaustiva de `routers/inventario.py`, `crud.py`, `models.py`/`schemas.py` y
`database.py` antes de diseñar nada:

- **Confirmado**: `get_historial_completo_producto` no existe en `crud.py` (búsqueda
  exhaustiva negativa) — el endpoint `GET /inventario/producto/{id}/historial` lo invoca
  igual, produciría `AttributeError` (500 no controlado) si se llamara. Nunca funcionó.
- **Confirmado**: existen `get_productos_bajo_stock`, `get_valor_total_inventario`,
  `get_estadisticas_dashboard` en `crud.py`, sobre `productos`/`movimientos`.
- **Corregido respecto al resumen previo de este plan**: **ninguno de los 5 endpoints de
  `inventario.py` tiene `require_authenticated` ni `require_super_admin`** — los 5 son
  100% públicos, a diferencia de casi todo lo demás en el legacy (`movimientos` protege la
  mayoría de sus endpoints, incluso GETs).
- **Corregido**: "bajo stock" es un `find()` con `$expr`, no un pipeline de `aggregate` —
  solo "valor total" usa un `$group` real.
- **Corregido**: `ReporteInventario`/`InventarioProducto` están duplicadas entre
  `models.py` y `schemas.py`, con `Producto`/`Movimiento` subyacentes **incompatibles
  entre sí** (una versión usa `id: int` estilo SQL legacy). Ninguna se usa como
  `response_model` real — el router devuelve dicts sueltos sin tipar. No hay DTO coherente
  que copiar.
- **Hallazgo nuevo**: `get_estadisticas_dashboard` devuelve `productos_bajo_stock` como
  **conteo**; `/bajo-stock` y `/reporte` lo devuelven como **lista** — mismo nombre de
  campo, semántica distinta.
- **Hallazgo nuevo**: el "historial de producto" que el endpoint roto pretendía ya está
  resuelto por el módulo `movimientos` ya migrado — `GET /api/movimientos?producto_codigo=X`
  (soporta `ListarMovimientosInput.producto_codigo`) hace exactamente eso. También existe
  `GET /api/movimientos/exportar/excel`, ya migrado con auth — no es parte de este módulo.

### Decisiones cerradas con el desarrollador

| Decisión | Elegido |
|---|---|
| Rol requerido en los 4 endpoints (legacy: público) | `require_authenticated` para todos, igual que el resto de lecturas ya migradas |
| Endpoint propio de "historial de producto" | Fuera de alcance — ya resuelto por `GET /api/movimientos?producto_codigo=X` |
| Endpoint `/reporte` (combinado, redundante con los otros 3) | Migrar, mantiene paridad con el legacy y evita 3 llamadas del frontend |

## Fase 2 — Domain + Application — APROBADA

- **Domain**: ninguna entidad propia — reutiliza `Producto` y `Movimiento` tal cual.
- **`ProductoRepositoryPort` extendido** (propiedad de `productos`, sin riesgo de ciclo —
  mismo criterio que `EjecutorDeMovimientosPort`) con 2 métodos nuevos, implementados en
  `MongoProductoRepository`:
  - `listar_bajo_stock() -> list[Producto]` — `find({"$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}})`.
  - `calcular_valor_total() -> float` — único `$group`/`$sum` real del módulo.
- **Sin cambios en `MovimientoRepositoryPort`**: `listar()` se reutiliza tal cual —
  `ListarMovimientosInput(pagina=1, limite=10)` da los últimos movimientos;
  `ListarMovimientosInput(fecha_desde=hoy_inicio, limite=1)` da el conteo de "movimientos
  de hoy" leyendo `total_elementos`, descartando la lista.
- **Sin cambios en `listar_paginado`** de `productos`: `listar_paginado(1, 1)` da el total
  de productos leyendo `total_elementos`.
- El conteo de "bajo stock" del dashboard se deriva con `len()` sobre `listar_bajo_stock()`
  — evita un tercer método del puerto solo para contar.
- **Services**: `ObtenerEstadisticasDashboardService`, `ListarProductosBajoStockService`,
  `ObtenerValorTotalInventarioService`, `ObtenerReporteInventarioService` (compone los 3
  anteriores).
- **DTOs de salida**: `EstadisticasDashboardOutput` (con `productos_bajo_stock_conteo: int`)
  y `ReporteInventarioOutput` (con `productos_bajo_stock: list[Producto]`) — nombres
  explícitamente distintos para no reproducir la colisión semántica del legacy.

## Fase 3 — Construcción (completa)

- **Rutas** (`/api/inventario`): `GET /dashboard`, `/bajo-stock`, `/valor-total`,
  `/reporte` — los 4 con `require_authenticated`.
- **Tests**: 9 nuevos — 3 en el repositorio Mongo de `productos`
  (`listar_bajo_stock`/`calcular_valor_total`) y 6 de aplicación en `inventario_reportes`
  (3 del dashboard, 1 de bajo-stock, 1 de valor-total, 1 del reporte consolidado) —
  329/329 en la suite completa.

### Verificación end-to-end (contra `inventario_db` real, con limpieza posterior)

`super_admin` + 2 productos de prueba (uno con `stock_actual=0 < stock_minimo=100`, otro
con una entrada real de 50 unidades a `precio_unitario=20.0`) → `GET /dashboard` sin token
(401) → con token (200, `total_productos=2`, `productos_bajo_stock_conteo=1`,
`movimientos_hoy=1`) → `GET /bajo-stock` incluye solo el producto bajo mínimo, excluye el
otro → `GET /valor-total` = `1000.0` (exactamente `50 * 20.0`, el producto bajo stock
aporta 0) → `GET /reporte` consistente con los 3 anteriores. Colecciones legacy
`productos`/`movimientos` verificadas con el mismo conteo antes y después (6/58
documentos, sin cambios — la nueva colección `catalogo_productos`/`registro_movimientos`
de `productos`/`movimientos` nunca las toca). Datos de prueba eliminados. Suite completa:
**329/329 tests verdes**.

### Checklist de migración

- [x] Domain — ninguna entidad propia (decisión de diseño, no pendiente)
- [x] Application — `ProductoRepositoryPort` extendido con 2 métodos + 4 servicios
- [x] Infrastructure — sin colección propia; 4 rutas HTTP, wiring cruzado con
  `productos`/`movimientos`
- [x] Bootstrap — `register_module(app)` registrado en `shared/bootstrap/application.py`
- [x] Tests — 9 nuevos, 329/329 en la suite completa
- [x] Verificación end-to-end completa contra `inventario_db` real, con limpieza de datos
  de prueba; legacy `productos`/`movimientos` intactos

## Observaciones

Primer y único módulo del plan que compone lectura de **dos** módulos a la vez
(`productos` + `movimientos`) exclusivamente por puerto, sin repositorio concreto ni
entidad propia — confirma que el patrón de composición entre módulos funciona en la
práctica. A diferencia de `aprobaciones_pendientes`, este módulo sí migra una capacidad
legacy real (dashboard/bajo-stock/valor-total funcionaban en producción), salvo el
historial de producto (roto, nunca migrado — resuelto por composición con `movimientos`)
y el hueco de seguridad (endpoints públicos, corregido a `require_authenticated`).

**Con el cierre de este módulo, la migración completa de `inventarios/app/` al backend
hexagonal queda terminada — no quedan módulos pendientes en este plan.**

---

# Anexo — Código legacy que NO debe migrarse (transversal, no ligado a un solo módulo)

| Archivo/elemento | Motivo |
|---|---|
| `crear_tablas.py` | Referencia `app.database.engine` y `app.models.Base` (SQLAlchemy) que **no existen** en el `database.py`/`models.py` actuales (que son 100% Mongo/Motor). Es un remanente de una versión anterior del proyecto sobre SQL. Completamente muerto. |
| `app/templates/*.html`, `app/static/*.html/js/css` (`app.js`, `style.css`, `qr-scanner.js`) | Fuera de alcance por decisión de arquitectura (backend solo-API, ver tabla de decisiones). |
| `app/main.py` (montaje de `Jinja2Templates`, `StaticFiles`, rutas HTML, `SessionMiddleware` si Google OAuth no termina necesitándolo) | Ídem — no aplica a un backend solo-API. Las piezas de configuración de app (CORS, lifespan de Mongo, exception handlers) sí tienen equivalente en `shared/bootstrap/application.py`, que ya existe en el proyecto nuevo y debe extenderse, no recrearse. |
| Clases duplicadas y sombreadas en `app/models.py` (primer `Movimiento`) y `app/schemas.py` (primer `ProductoBase`/`ProductoUpdate`, familia `UserLogin`/`UserRegister` si se confirma no usada) | Quedaron sombreadas por una segunda definición en el mismo archivo — indican iteraciones de parcheo sin limpieza. Usar solo la versión vigente (la que el código realmente ejecuta) como referencia. |
| Bloques `except Exception as e: print(...)` / `except: pass` genéricos | Reemplazar sistemáticamente por `DomainError` tipados, capturados en la capa HTTP (ver `.claude/CONVENTIONS.md` y `shared/domain/errors.py`, que ya define `ErrorCategory`). |
| `print()` de depuración con emojis (🔵 ❌ ✅ 📍 ...) en prácticamente todos los archivos | Reemplazar por el logger ya configurado en el proyecto nuevo (`config/logger.py`, referenciado desde `shared/bootstrap/application.py`). |

---

# Deuda pendiente detectada al validar el frontend legacy contra el backend nuevo

Después de cerrar los 8 módulos, se corrió el frontend legacy (`front---proyecto`, Next.js) contra
este backend para validar el sistema completo de punta a punta. Esa validación adaptó las llamadas
del frontend a las rutas reales (ver `docs/api/*.md` para el contrato completo, sección por
módulo) y confirmó que casi todo el catálogo de negocio ya tiene equivalente — con estas
excepciones concretas, que **son huecos reales del backend**, no solo de mapeo del frontend:

| Funcionalidad legacy | Estado en el backend nuevo | Nota |
|---|---|---|
| Generar código QR de un producto (`GET /productos/{id}/qr-code`) | **No existe** | Ninguna dependencia de generación de QR en el proyecto nuevo. El legacy lo generaba on-the-fly; nunca se migró. |
| Subir/eliminar imagen de producto (`POST/DELETE /productos/{id}/subir-imagen`, `/eliminar-imagen`) | **No existe** | `Producto.imagen_url` existe en la entidad pero es de solo lectura vía API — `Producto.actualizar()` lo excluye explícitamente ("incremento futuro con su propio service dedicado", ver `modules/productos/domain/entities/producto.py`). No hay `StorageRepositoryPort` cableado para productos (sí existe y se usa en `movimientos` para PDFs — reutilizable). |
| Carga masiva de productos por Excel + plantilla descargable (`POST /productos/cargar-excel`, `GET /productos/plantilla-excel`) | **No existe** | Solo existe exportación de movimientos a Excel (`GET /movimientos/exportar/excel`). Nunca se migró la carga masiva de productos. |
| Proponer un "kit" o una "salida por mercado predefinido" como pendiente de aprobación | **Fuera de alcance, decisión explícita** | `aprobaciones_pendientes` solo admite `entrada`, `entrada_multiple`, `salida`, `salida_multiple` (ver su sección de Fase 0). Un kit/mercado solo puede registrarse directo (`POST /movimientos/salida-por-mercado`, sin equivalente de "kit" directo tampoco) o vía el carrito de `reservas` (`ConfirmarReservaService` sí soporta modalidad kit/múltiple/normal). |
| "Confirmar varias salidas a la vez con número de cajas + una remisión consolidada" | **No existe como operación atómica** | El legacy lo orquestaba desde el cliente (loop de guardar-reserva + confirmar por cada salida). El backend nuevo solo confirma **una reserva de sesión a la vez** (`POST /movimientos/reservas/{session_id}/confirmar`) o **una pendiente a la vez** (`POST /aprobaciones-pendientes/{id}/confirmar`). No hay un endpoint de "confirmar N a la vez con conteo de cajas". |
| Comprobante PDF consolidado de varias salidas (`POST /movimientos/comprobante-multiple`) | **No existe** | Solo existe comprobante de una salida individual (`GET /movimientos/{id}/comprobante`). |

**Lo que SÍ existe pero el frontend legacy llamaba con una ruta distinta** (esto no es deuda del
backend — quedó resuelto adaptando el frontend, se documenta acá solo para que quien migre el
frontend no lo redescubra):

| El frontend legacy llamaba... | La ruta real es... |
|---|---|
| `GET/POST /productos/{id}/con-ubicaciones` | `GET/POST /api/productos/{codigo}/ubicaciones` (módulo `ubicaciones`, montado bajo el prefijo de `productos`) |
| `POST /productos/{id}/transferir` | `POST /api/productos/{codigo}/ubicaciones/transferir` |
| `PUT/DELETE /productos/{id}/ubicaciones/{ubicacion}` | Coincide tal cual, ya existía |
| `GET /productos/{id}/stock-por-ubicacion` | No hay un endpoint agregado equivalente — se compone en el cliente combinando `GET /productos/{codigo}/ubicaciones` (stock físico) + `GET /reservas/stock-disponible/{producto_codigo}/{ubicacion}` (stock disponible con reservas) |
| `POST /movimientos/`, `POST /movimientos/entrada-multiple`, `POST /movimientos/salida-multiple` | `POST /movimientos/entradas`, `POST /movimientos/entradas/multiple`, `POST /movimientos/salidas`, `POST /movimientos/salidas/multiple` |
| `GET /movimientos/salida/{id}/pdf`, `POST /movimientos/{id}/subir-pdf` | `GET /movimientos/{id}/comprobante`, `POST /movimientos/{id}/pdf-firmado` |
| `GET /auth/me` (el frontend ya lo llamaba) | No existía — **se agregó** en esta validación (`modules/auth/infrastructure/api/routes.py`), es idiomático, no es un hueco pendiente. |

Ver `MIGRACION_PLANFRONTEND.md` (en el repo del frontend nuevo) para el plan de migración del
frontend a arquitectura hexagonal, que parte de esta misma tabla.

---

# Próximos pasos

Los 8 módulos identificados (`auth`, `productos`, `ubicaciones`, `mercados_predefinidos`,
`reservas`, `movimientos`, `aprobaciones_pendientes`, `inventario_reportes`) están **CERRADOS**
— ver la sección propia de cada uno para su Fase 0, decisiones y verificación end-to-end. La
migración completa de `inventarios/app/` (legacy) al backend hexagonal (`template-fastapi-backend`)
ha terminado: no queda ningún módulo pendiente en este plan.

Este documento queda como referencia histórica de las decisiones de diseño tomadas durante la
migración — útil para entender el *por qué* detrás de cada módulo nuevo, no solo el *qué*.
