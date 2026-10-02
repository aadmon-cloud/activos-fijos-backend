# API — Módulo de Autenticación

**Base:** `/api/auth` · **Auth:** Bearer token (excepto donde se indica público)

Login, registro, recuperación de password, Google OAuth y gestión administrativa de
usuarios. Es el punto de entrada de todo el sistema: el token que emite `/login` se usa en
el header `Authorization: Bearer <token>` para el resto de los módulos.

---

## 1. Convenciones de respuesta

**Errores** (todo el sistema, no solo `auth`):

```json
{
  "status": "error",
  "code": "AUTH-001",
  "message": "Email o contraseña incorrectos.",
  "category": "unauthorized",
  "path": "/api/auth/login",
  "metadata": {}
}
```

| Categoría | HTTP |
|---|---|
| `validation` | 400 |
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `not_found` | 404 |
| `conflict` | 409 |
| `business_rule` | 422 |
| `integration` | 502 |
| `internal` | 500 |

**Paginación** (usuarios):
```json
{ "resultado": [...], "pagina_actual": 1, "elementos_por_pagina": 10, "total_elementos": 42, "total_paginas": 5 }
```

## 2. Tipos y enums

`rol`: `"super_admin" | "admin" | "operativo"` (jerárquico, ver Notas de comportamiento).

```json
// UsuarioResponse
{ "id": "...", "email": "a@b.com", "username": "abarrios", "rol": "operativo", "activo": true }
```

## 3. Flujos

- **Usuario nuevo**: `POST /registro` → `POST /login` → guardar el token, usarlo en todos los requests siguientes.
- **Olvidé mi password**: `POST /forgot-password` (siempre 200, revele o no el email) → revisar email → `POST /reset-password` con el token recibido.
- **Login con Google**: redirigir el navegador a `GET /google` → Google redirige de vuelta al frontend con `?token=...` en la URL de callback configurada.
- **Admin gestiona usuarios**: ⚠️ un `super_admin` no puede editarse ni eliminarse a sí mismo por `/usuarios/{id}` (usar su propio flujo de `change-password`).

## 4. Endpoints públicos

### POST `/api/auth/login` — autentica y emite token · público

```json
{ "email": "a@b.com", "password": "clave12345" }
```
Respuesta: `{ "access_token": "...", "token_type": "bearer", "usuario": {...} }`
Errores: `AUTH-001` (401, credenciales inválidas), `AUTH-002` (403, usuario desactivado).

### POST `/api/auth/registro` — alta pública · público

```json
{ "email": "a@b.com", "password": "clave12345", "confirm_password": "clave12345", "username": "abarrios" }
```
Rol siempre `operativo`, sin importar lo que se envíe. `username` opcional (se deriva del
email); si colisiona, se le agrega un sufijo aleatorio automático.
Errores: `AUTH-004` (400, passwords no coinciden), `AUTH-003` (409, email ya registrado).

### POST `/api/auth/forgot-password` — solicita recuperación · público

`{ "email": "a@b.com" }` → siempre `200 { "message": "..." }`, exista o no el email (no filtra información).

### POST `/api/auth/reset-password` — aplica nueva password · público

`{ "token": "...", "new_password": "...", "confirm_password": "..." }`
Errores: `AUTH-008` (400, token inválido/expirado), `AUTH-004` (400, passwords no coinciden).

### GET `/api/auth/google` — inicia login con Google · público

Redirige (307) a la pantalla de consentimiento de Google. Error: `AUTH-011` (500, no configurado).

### GET `/api/auth/google/callback` — callback de Google · público

Redirige a `{FRONTEND_URL}/auth/google-callback?token=...`. Errores: `AUTH-002` (403), `AUTH-010` (502, falla el intercambio con Google).

## 5. Endpoints autenticados

### POST `/api/auth/change-password` — cambia password · `require_authenticated`

`{ "current_password": "...", "new_password": "...", "confirm_password": "..." }`
Errores: `AUTH-009` (401, password actual incorrecta), `AUTH-004` (400).

## 6. Endpoints admin (`super_admin`)

### GET `/api/auth/usuarios` — lista paginada · `require_super_admin`

Query: `?pagina=1&limite=10`.

### POST `/api/auth/usuarios` — crea con rol explícito · `require_super_admin`

`{ "email": "...", "username": "...", "password": "...", "rol": "admin" }` (password opcional). Error: `AUTH-003` (409).

### PUT `/api/auth/usuarios/{usuario_id}` — update parcial · `require_super_admin`

`{ "username": "...", "rol": "...", "activo": false, "password": "..." }` (todo opcional).
Errores: `AUTH-013` (400, ⚠️ no podés editarte a vos mismo por esta vía), `AUTH-012` (404).

### DELETE `/api/auth/usuarios/{usuario_id}` — elimina · `require_super_admin`

Errores: `AUTH-013` (400, ⚠️ no podés eliminarte a vos mismo), `AUTH-012` (404).

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|
| `AUTH-001` | 401 | Email o password incorrectos | Mostrar error genérico, no indicar cuál campo falló |
| `AUTH-002` | 403 | Usuario desactivado | "Contactá al administrador" |
| `AUTH-003` | 409 | Email ya registrado | Sugerir login o recuperar password |
| `AUTH-004` | 400 | Las contraseñas no coinciden | Resaltar ambos campos de password |
| `AUTH-005` | 401 | Token inválido/expirado | Forzar logout, redirigir a login |
| `AUTH-006` | 401 | Usuario del token ya no existe | Forzar logout |
| `AUTH-007` | 403 | Rol insuficiente | Ocultar la acción en la UI para ese rol |
| `AUTH-008` | 400 | Token de recuperación inválido/expirado | Volver a pedir "olvidé mi password" |
| `AUTH-009` | 401 | Password actual incorrecta | Resaltar el campo de password actual |
| `AUTH-010` | 502 | Falla el intercambio con Google | Reintentar login con Google |
| `AUTH-011` | 500 | Google OAuth no configurado en el servidor | Ocultar el botón de "Login con Google" |
| `AUTH-012` | 404 | No existe el usuario | Refrescar el listado |
| `AUTH-013` | 400 | Operación sobre el propio usuario no permitida | Explicar que debe usar "cambiar mi password" |

## Notas de comportamiento

- El JWT incluye `sub` (id de usuario) y `rol`; expira según `JWT_EXPIRE_MINUTES` (default 480 min).
- `email` se normaliza a minúsculas siempre.
- No hay invalidación/blacklist de tokens — el logout es solo del lado del cliente (descartar el token).
- Roles jerárquicos: `super_admin` > `admin` > `operativo`, pero cada módulo declara explícitamente qué roles acepta (no hay herencia automática de permisos entre módulos).
