# Módulo `auth`

> Estado: **cerrado** (4/4 incrementos). Ver `MIGRATION_PLAN.md` para el historial completo
> de decisiones, hallazgos y verificaciones de cada incremento.

## Responsabilidad

Autenticar usuarios (email/password y Google OAuth), emitir/validar JWT, gestionar roles
(`super_admin`, `admin`, `operativo`) y administrar el ciclo de vida de cuentas de usuario.
Es el módulo fundacional: expone la dependencia HTTP "usuario actual" que consumen todos
los demás módulos protegidos.

## Entidades

- **`Usuario`** (`domain/entities/usuario.py`): `id`, `email`, `username`, `password_hash`
  (nulo si es cuenta solo-Google), `rol`, `activo`, `email_verificado`, `google_id`,
  `google_picture`, `reset_password_token`, `reset_password_expires`, `creado_por`,
  `actualizado_por`. Métodos de transición: `crear()`, `crear_desde_google()`,
  `crear_por_admin()`, `vincular_google()`, `generar_token_reset()`,
  `restablecer_password()`, `cambiar_password()`, `actualizar_admin()`.
- **`RolUsuario`** (enum): `super_admin`, `admin`, `operativo`. Jerárquico — ver Notas de
  permisos abajo.

## Casos de uso (servicios)

| Servicio | Qué hace |
|---|---|
| `LoginService` | Email/password → JWT |
| `RegistrarUsuarioService` | Alta pública, rol siempre `operativo`, sufijo automático si el username colisiona |
| `SolicitarRecuperacionPasswordService` | Genera token de reset (1h), envía email (best-effort) |
| `RestablecerPasswordService` | Aplica nueva password con token válido |
| `CambiarPasswordService` | Cambio autenticado, valida password actual |
| `IniciarLoginGoogleService` / `LoginConGoogleService` | OAuth manual (intercambio de código vía `httpx`, sin `authlib`) |
| `ListarUsuariosService` | Paginado, solo `super_admin` |
| `CrearUsuarioAdminService` | Alta con rol explícito, solo `super_admin` |
| `ActualizarUsuarioAdminService` | Update parcial (username/rol/activo/password), solo `super_admin` |
| `EliminarUsuarioAdminService` | Baja, solo `super_admin` |

## Colecciones Mongo

- **`usuarios`** (no `users` — colisión con datos reales del legacy, ver hallazgo en
  `MIGRATION_PLAN.md`). Índices: único en `email`, único en `username`, sparse en
  `google_id`, sparse en `reset_password_token`, normal en `creado_por.fecha`.

## Dependencias con otros módulos

Ninguna hacia adentro. Expone `shared/infrastructure/api/dependencies/auth.py`
(`get_current_usuario`, `require_authenticated`, `require_admin_or_super`,
`require_super_admin`), consumido por `productos`, `ubicaciones`, `mercados_predefinidos`,
`reservas` y todo módulo futuro que necesite autenticación.

## Flujos principales

1. **Registro → login**: `POST /registro` (rol `operativo` forzado) → `POST /login` → JWT.
2. **Recuperación de password**: `POST /forgot-password` (siempre responde igual, exista o no
   el email) → email con token (1h) → `POST /reset-password`.
3. **Google OAuth**: `GET /google` (redirige a Google) → `GET /google/callback` (intercambia
   código, crea o vincula usuario, redirige al frontend con el JWT en query param).
4. **Gestión admin**: CRUD completo de usuarios bajo `/usuarios/*`, exclusivo `super_admin`,
   con protección explícita contra auto-edición/auto-eliminación (`AUTH-013`).

## Notas de permisos

Los 3 roles son jerárquicos (`super_admin` > `admin` > `operativo`), tal como se modela en
`RolUsuario`. `require_authenticated` acepta cualquiera de los 3. Los módulos de negocio
construidos hasta ahora (`productos`, `ubicaciones`, `mercados_predefinidos`) usan
`require_authenticated` genérico para escritura. `reservas` es el primero en introducir
distinción por rol específico (`require_super_admin` para eliminar) — ver
`MIGRATION_PLAN.md`, sección `reservas`, para el criterio completo de permisos por rol
acordado con el desarrollador (aplica también a `movimientos`, todavía no construido).

## Decisiones de diseño relevantes

Ver `MIGRATION_PLAN.md`, sección "Módulo `auth`", para: por qué `usuarios` y no `users`,
por qué se descartó `authlib` en favor del intercambio manual de OAuth, el bugfix de
`creado_por` pisado en `crear()`, y el hallazgo de que el servidor Mongo era standalone
(resuelto convirtiéndolo a replica set de un nodo, habilitando `MongoUnitOfWork` para
módulos futuros).
