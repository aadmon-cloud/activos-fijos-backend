# API — Patrones HTTP

## Ruta estándar

```python
# modules/<modulo>/infrastructure/api/routes.py
router = APIRouter(prefix="/api/xxx", tags=["xxx"])

@router.post(
    "",
    status_code=201,
    summary="Crea un nuevo xxx",
    responses={
        409: {"description": "Conflicto de negocio (p. ej. duplicado)"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
async def crear_xxx(
    body: CrearXxxRequest,
    service: Annotated[CrearXxxService, Depends(get_crear_xxx_service)],
):
    resultado = await service.ejecutar(CrearXxxDTO(...))
    return {
        "status": "success",
        "message": "Xxx creado exitosamente.",
        "data": XxxResponse(...).model_dump(),
    }
```

## Envelope de respuesta

Toda ruta retorna un `dict` plano (no un `response_model` Pydantic aplicado al
envelope en sí) con una de estas tres formas de éxito:

```python
{"status": "success", "data": {...}}                            # consultas
{"status": "success", "message": "...", "data": {"id": "..."}}  # creaciones
{"status": "success", "message": "..."}                         # acciones sin data
```

Como las rutas ya no usan anotación de retorno `-> XxxResponse` ni
`response_model=`, el body de éxito queda **sin tipar** en el schema
OpenAPI/Swagger generado. `XxxResponse` sigue existiendo como fuente de
verdad del shape de `data` en el lado Python (se usa vía `.model_dump()` para
construirlo), pero ya no aparece como el response schema documentado del
endpoint en Swagger. Es un trade-off aceptado del patrón de dict inline, no
un descuido.

## Inyección de dependencias

```python
# modules/<modulo>/infrastructure/api/dependencies.py
from functools import lru_cache


@lru_cache(maxsize=1)
def get_xxx_repository() -> XxxRepositoryPort:
    return MongoXxxRepository()


def get_crear_xxx_service() -> CrearXxxService:
    return CrearXxxService(xxx_repository=get_xxx_repository())
```

La ruta recibe el servicio ya construido. Nunca instanciar repositorios o servicios dentro del handler.

## Reglas de documentación

- `summary` obligatorio: verbo en tercera persona ("Crea", "Obtiene", "Lista", "Elimina").
- `responses` solo para errores 4xx de negocio relevantes. No documentar 500.
- No usar `description=` en el decorador salvo comportamiento no obvio.
- No docstrings en la función de ruta.

## Schemas HTTP

Viven en `infrastructure/api/schemas.py`. Separar request de response:

```python
class CrearXxxRequest(BaseModel): ...
class XxxResponse(BaseModel): ...
```

## Registro del módulo

```python
# modules/<modulo>/bootstrap.py
def register_module(app: FastAPI) -> None:
    app.include_router(router)
```

Registrado en `shared/bootstrap/application.py`.

## Manejo de errores de dominio

Los errores de dominio (`DomainError` y subclases) se capturan globalmente en
`shared/infrastructure/api/error_handlers.py` y se convierten a:

```json
{
  "status": "error",
  "code": "XXX-001",
  "message": "mensaje legible",
  "category": "not_found",
  "path": "/api/xxx/123",
  "metadata": {}
}
```

El HTTP status se deriva de `category` vía `STATUS_BY_CATEGORY` (no se declara
por subclase):

| Categoría | HTTP |
|---|---|
| `validation` | 400 |
| `not_found` | 404 |
| `conflict` | 409 |
| `business_rule` | 422 |
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `integration` | 502 |
| `internal` | 500 |

Cada subclase de `DomainError` pasa `code` y `category` a `super().__init__()`:

```python
class XxxNoEncontradoError(DomainError):
    def __init__(self, id_xxx: str):
        super().__init__(
            f"El xxx '{id_xxx}' no existe.",
            code="XXX-001",
            category=ErrorCategory.NOT_FOUND,
        )
```

Cualquier excepción no controlada (no `DomainError`) se convierte en un `500`
con `code: "GEN-500"`, sin registro adicional — no debe llegar al cliente
como un error sin envelope.

El envelope de `GEN-500` **no** incluye `category` ni `metadata` (a diferencia
de la respuesta de un `DomainError`) — ningún frontend debe asumir que todo
body con `status: "error"` trae el mismo set de claves.

Los errores `422` que arma FastAPI automáticamente (body/query no cumple el
schema Pydantic) **no** pasan por este envelope — quedan con el shape default
de FastAPI (`{"detail": [...]}`), distinto de un `DomainError` de categoría
`validation`.

## Sesión de usuario (cookie HttpOnly)

- **El ingreso es solo con Google.** `POST /api/usuarios/login/google` `{credencial, nonce}` abre la sesión con `Set-Cookie: <COOKIE_NAME>=<jwt>; HttpOnly; Secure; SameSite; Path=/api; Max-Age`. El cuerpo trae solo `data.usuario`; el token **no** va en el cuerpo.
  - `credencial` es el token de identidad (OpenID Connect) que Google entrega al navegador; `nonce` es el que el navegador generó para ese intento. Se valida firma, audiencia (`GOOGLE_CLIENT_ID`), vigencia, **correo verificado**, que el token tenga **menos de 5 minutos** y que su `nonce` coincida.
  - **Solo entran usuarios ya registrados y activos** (el correo certificado por Google debe coincidir con el de un usuario). Nadie se crea solo; el rol y el área son los que asignó el administrador.
  - Errores: `401 USR-009` token inválido; `401 USR-010` la cuenta no está registrada o está desactivada; `502 USR-011` falta `GOOGLE_CLIENT_ID`.
  - `POST /api/usuarios/login` (correo y contraseña) está **deshabilitado**: responde `403 USR-012`. Solo se reabre con `LOGIN_PASSWORD_HABILITADO=true`, pensado únicamente para pruebas automatizadas en local.
  - Registrar un usuario ya no pide contraseña (queda una que nadie conoce). El primer administrador se crea con `python -m scripts.crear_administrador --email … --nombre … --apellido …`.
- `POST /api/usuarios/logout` expira la cookie.
- `requiere_usuario_autenticado` lee la cookie y acepta `Authorization: Bearer` como alternativa (pruebas y clientes no navegador). La cookie tiene prioridad.
- **CSRF:** toda petición `POST/PUT/PATCH/DELETE` que viaje con la cookie de sesión debe enviar `X-Requested-With: XMLHttpRequest` (`CsrfHeaderMiddleware`); si falta, `403 AUTH-004`.
- **CORS:** `CORS_ORIGINS` (lista JSON) es obligatoria para clientes de navegador; nunca `*` porque se usan credenciales.
- Configuración: `COOKIE_NAME`, `COOKIE_SECURE` (`false` solo en local sobre http), `COOKIE_SAMESITE`, `COOKIE_DOMAIN`.

| Código | Categoría | Cuándo |
|---|---|---|
| `AUTH-001` | unauthorized (401) | No hay sesión |
| `AUTH-002` | unauthorized (401) | Token inválido o expirado |
| `AUTH-003` | forbidden (403) | El rol no permite la acción |
| `AUTH-004` | forbidden (403) | Falta la cabecera CSRF |

## Usuarios: reactivar y contraseñas

| Método | Ruta | Quién | Efecto |
|---|---|---|---|
| `POST` | `/api/usuarios/{id}/reactivar` | `administrador_general` | Reactiva un usuario desactivado (idempotente). `404 USR-005` si no existe |
| `PUT` | `/api/usuarios/{id}/password` | `administrador_general` | Restablece la contraseña. Body `{password_nueva}` (mín. 8). `400 USR-003` si es débil |
| `PUT` | `/api/usuarios/me/password` | usuario autenticado | Cambia la propia. Body `{password_actual, password_nueva}`. `400 USR-007` actual incorrecta, `422 USR-008` nueva igual a la actual |

Estado de la sesión en cada petición: aunque el JWT es sin estado, `requiere_usuario_autenticado` consulta el usuario en la base de datos (`ConsultaEstadoUsuarioMongo`) en **cada** petición. Si el usuario fue desactivado o ya no existe responde `401 AUTH-002`, y el **rol** que se usa es el vigente en la base de datos, no el del token. Así, desactivar a alguien o cambiarle el rol surte efecto de inmediato. Cuesta una lectura por `_id` (con proyección de `activo` y `rol`) por petición; si llega a pesar, se añade un caché corto.

Cambiar o restablecer una contraseña **no cierra** las sesiones ya abiertas de ese usuario (no hay revocación por contraseña); solo desactivarlo lo hace.

## Activos: listado con total y nombres

`GET /api/activos` (cualquier usuario autenticado) devuelve ahora, además de `data`, un bloque `meta` con el total que cumple los filtros, para paginar en el servidor:

```json
{ "status": "success", "data": [ { ...activo, "categoria_nombre": "...", ... } ],
  "meta": { "total": 1498, "skip": 0, "limit": 50 } }
```

Cada activo (listado y `GET /api/activos/{id}`) incluye los nombres vigentes de sus referencias: `categoria_nombre`, `area_nombre`, `responsable_nombre` (nombre y apellido), `condicion_nombre`, `condicion_color`, `sede_nombre`, `lugar_nombre`. Un valor es `null` si el registro referenciado ya no existe. Se resuelven en una sola consulta por catálogo (puerto `ResolutorNombresPort`, adaptador `MongoResolutorNombres`), de modo que un empleado ve los nombres sin necesitar `GET /api/usuarios` (solo administrador). Las respuestas de crear, editar y cambiar estado no incluyen los nombres.

La búsqueda (`busqueda`) trata el texto como literal: se escapa antes de usarlo como expresión regular (antes era una expresión arbitraria: riesgo de inyección y ReDoS).

`GET /api/activos/{id}/historial` incluye `valor_anterior_nombre` y `valor_nuevo_nombre` para los campos que guardan un id (`responsable_id`, `area_id`, `condicion_id`, `sede_id`, `lugar_id`); para `estado_ciclo_vida` los valores ya son legibles y los nombres vienen `null`. Si el registro referenciado ya no existe, el nombre es `null` y queda el id.

## Activos: sin valor ni fecha de adquisición

Los activos ya no tienen `valor` ni `fecha_adquisicion` (ni en el alta, ni en la edición, ni en la respuesta); el error `ACT-004` (valor inválido) dejó de existir. La respuesta incluye `fecha_ingreso`: el momento en que el sistema registró el activo (la fecha de creación del registro, que asigna el backend y no se puede editar). Los documentos antiguos que aún tengan esos campos en Mongo se leen sin problema: simplemente se ignoran. `ficha_tecnica_url` se conserva en el backend pero el frontend no la usa todavía (la subida de documentos queda para después).

## Activos: fotografía

Una foto por activo, guardada en MongoDB (GridFS, bucket `activos_fotos`) y servida siempre por un endpoint autenticado: nunca hay un enlace público.

| Método | Ruta | Quién | Efecto |
|---|---|---|---|
| `PUT` | `/api/activos/{id}/foto` | `administrador_general` | El **cuerpo es la imagen en bruto** (no multipart). Crea o reemplaza la foto y deja `foto_url` del activo en `/api/activos/{id}/foto` |
| `GET` | `/api/activos/{id}/foto` | cualquier usuario autenticado | Devuelve la imagen con su `Content-Type` y `Cache-Control: private, max-age=300` |
| `DELETE` | `/api/activos/{id}/foto` | `administrador_general` | Elimina la foto y limpia `foto_url` |

Reglas: solo JPEG, PNG o WebP, hasta 5 MB. El tipo se decide por los **primeros bytes del archivo**, no por el `Content-Type` que declare el cliente (un SVG con scripts enviado como `image/png` se rechaza). Si el `Content-Length` declarado ya supera el máximo se rechaza antes de leer el cuerpo.

| Código | Cuándo |
|---|---|
| `ACT-006` (400) | No es JPEG, PNG ni WebP |
| `ACT-007` (400) | Supera 5 MB |
| `ACT-008` (404) | El activo no tiene foto |

Al reemplazar, la foto nueva se sube primero y las anteriores se borran después, para no perder la foto si la subida falla.

## Solicitudes: visibilidad, permisos y respuesta enriquecida

**Visibilidad.** Cada usuario ve solo las solicitudes que creo, las asignadas a su rol (`rol_asignado`) o las de su
area (`area_id`). `administrador_general` ve todas. Una solicitud que el usuario no puede ver responde `404 SOL-001`
(no `403`) en detalle, cambio de estado y seguimiento, para no revelar que existe. El rol y el area se leen de la
base en cada peticion, no del token.

**Permisos por accion.**

| Accion | Quien puede |
| --- | --- |
| Crear | Responsable del activo o administrador (`SOL-003` si no) |
| Comentar (`POST /{id}/seguimiento`) | Quien pueda verla |
| Pasar a `en_proceso`, `resuelta` o `rechazada` | Administrador, o el equipo asignado **que no sea el solicitante** |
| Pasar a `cerrada` | Administrador o el solicitante (el equipo no cierra lo que resolvio) |

Sin permiso para el cambio: `403 SOL-005`. Transicion fuera del flujo: `422 SOL-004`.

**Listado `GET /api/solicitudes`** — filtros `tipo`, `estado`, `activo_id`, `rol_asignado`, `area_id`, `creado_por_id`,
`skip`, `limit`. Los filtros se combinan con la visibilidad (AND). Devuelve `meta: {total, skip, limit}` y, por item:
`creado_por_id`, `creado_por_nombre`, `fecha_creacion`, `fecha_actualizacion`, `activo_nombre`,
`activo_numero_inventario`, `area_nombre`. `area_nombre` es el area a la que se enruto la solicitud: es `null` en
`mantenimiento` y `cambio`, que se asignan por rol.

**Detalle `GET /api/solicitudes/{id}`** — lo anterior mas `estados_permitidos` (estados a los que *este* usuario puede
pasarla ahora; el frontend no debe recalcularlos) y `puede_comentar`.

**`POST /api/solicitudes`** responde solo `{id}`; el frontend consulta el detalle despues.

## Usuarios: identificacion opcional

El indice unico de `identificacion` es parcial (`uq_identificacion_texto`, solo aplica a valores de tipo texto). El
indice `sparse` anterior no ignoraba los `null` explicitos y el segundo usuario sin identificacion fallaba con 500.
`crear_indices` retira el indice anterior (`uq_identificacion`) si existe.

## Solicitudes: efecto sobre el estado del activo

Al cambiar el estado de una solicitud, el backend actualiza el `estado_ciclo_vida` del activo (decision del
responsable: «al aceptar y al resolver»). Crear la solicitud **no** cambia el activo.

| Tipo de solicitud | Pasa a `en_proceso` (aceptada) | Pasa a `resuelta` |
| --- | --- | --- |
| `mantenimiento` | activo → `en_mantenimiento` | activo → `disponible`, solo si sigue en `en_mantenimiento` |
| `reporte_dano` | activo → `danado` | sin cambio |
| `reporte_perdida` | activo → `perdido` | sin cambio |
| `cambio`, `ajuste` | sin cambio | sin cambio |

`rechazada` y `cerrada` nunca tocan el activo.

- **Quien actua queda en el historial del activo** (`estado_ciclo_vida`, con su nombre). El cambio lo hace el servicio
  de activos, asi que se aplica la misma matriz de transiciones (`ACT-003`) y no se escribe a mano en la coleccion.
- **Un tecnico no necesita el permiso de administrador de activos** para que el activo cambie: lo hace la regla,
  solo mediante una solicitud que el usuario si puede gestionar.
- **Si la transicion del activo no es valida** (p. ej. un activo `prestado` que entra a mantenimiento), la solicitud
  avanza igual y el seguimiento lo anota: «No se cambio el estado del activo: no puede pasar de 'X' a 'Y'. Revisarlo
  manualmente.» Lo mismo si el activo ya estaba en el estado destino o si ya no existe: no se anota nada.
- **El activo se actualiza antes de guardar la solicitud.** Si falla, la solicitud no cambia y no quedan desalineados.
- Cada cambio agrega al seguimiento una segunda entrada sin `estado_anterior`/`estado_nuevo` con el texto
  «El estado del activo cambio de 'A' a 'B'.».
- Regla pura en `modules/solicitudes/domain/efecto_en_activo.py`; el puerto es `ActivoEstadoPort` y su adaptador
  (`infrastructure/adapters/activo_estado_adapter.py`) es el **unico** archivo de solicitudes que usa codigo del
  modulo `activos`: se reutiliza su servicio para no duplicar transiciones ni historial.

## Movimientos: varios activos, doble aprobacion, chequeo de salida e ingreso y actas

Un movimiento (`prestamo`, `salida_evento`, `baja`) tiene **varios items** (un activo cada uno) y cada item sigue su
propio recorrido. El estado del movimiento se **calcula** a partir de sus items (salvo la baja, explicita).

| Estado del item | Significa |
| --- | --- |
| `pendiente_responsable` | Espera que el responsable **actual** del activo apruebe o rechace |
| `pendiente_admin` | El responsable aprobo (o quien lo pide ya es el responsable): espera a administracion |
| `rechazado` | Rechazado por el responsable o por administracion (`etapa_rechazo`, `motivo_rechazo`) |
| `en_curso` | Salio: el activo quedo `prestado` a cargo del destinatario |
| `devolucion_solicitada` | Quien lo tiene pidio devolverlo |
| `devuelto` | Administracion lo recibio (bien o con novedad); volvio a `disponible` y a su responsable original |
| `ejecutado` | Baja ejecutada |

Estado del movimiento: `solicitado` (algun item espera a su responsable) → `aprobado_responsable` (todos decidieron y
hay uno aprobado) → `en_curso` → `devuelto`; `rechazado` si todos se rechazaron. Baja: `solicitado` → `aprobado` →
`ejecutado`.

**Solicitar `POST /api/movimientos`** `{tipo, activo_ids[], descripcion, sentido?, usuario_destino_id?, evento_nombre?,
fecha_salida_estimada?, fecha_retorno_estimada?}`. Maximo 200 activos; los repetidos se cuentan una vez.
- `prestamo` exige `sentido`: **`prestar`** (el activo es de quien lo monta y elige el destinatario; un empleado solo
  presta lo suyo, `MOV-019`; un administrador puede montarlo en nombre de otro, y entonces el responsable aprueba) o
  **`solicitar`** (pide activos de otros; el destinatario es quien pide).
- En `solicitar` y en la salida a evento solo un administrador puede elegir otro destinatario (`MOV-020`).
- Si quien lo pide ya es el responsable de un activo, ese item nace `pendiente_admin`. La baja nace `pendiente_admin`.
- Cada activo debe existir (`MOV-001`), estar `disponible` (`MOV-003`) y no estar en otro movimiento sin terminar
  (`409 MOV-004`).
- Validaciones `400`: `MOV-012` descripcion vacia; `MOV-013` falta destinatario al prestar; `MOV-014` evento sin
  nombre; `MOV-015` fechas invertidas; `MOV-016` sin activos; `MOV-017` baja de mas de un activo; `MOV-018` prestamo
  sin sentido; `MOV-024` prestar a su propio responsable. Baja solo del administrador (`MOV-010`).

**Visibilidad.** El administrador ve todo. Los demas ven lo que crearon, donde son destinatarios o responsables
(original o actual) de algun activo. Lo que no pueden ver responde `404 MOV-005`.

**Listado `GET /api/movimientos`** — filtros `tipo`, `estado`, `activo_id` (movimientos que lo incluyen),
`usuario_destino_id`, `creado_por_id`, `skip`, `limit` y **`para_mi=true`**: lo que le concierne como destinatario o
responsable de algun activo (al administrador, ademas, lo que espera una accion suya). "Mis solicitudes" es
`creado_por_id`. Devuelve `meta: {total, skip, limit}`.

**Cada movimiento (listado y detalle) trae** `usuario_destino_nombre`, por item `activo_nombre`,
`activo_numero_inventario`, `responsable_original_nombre` y `acciones_permitidas`, y en total `acciones_permitidas`.
Las decide el backend; el frontend no las recalcula.

| Accion (ruta) | Quien | Sobre que items |
| --- | --- | --- |
| `aprobar` (`POST /{id}/aprobar`) | El responsable actual de cada activo; en una baja, el administrador | `pendiente_responsable` (o la baja `solicitada`) |
| `rechazar` (`POST /{id}/rechazar`, con `motivo_rechazo`) | Igual que aprobar; el administrador tambien los `pendiente_admin` | Los que esa persona puede decidir |
| `confirmar_salida` (`PUT /{id}/items/{activo_id}/chequeo` y `POST /{id}/confirmar-salida`) | Administrador | `pendiente_admin` (prestamo y evento): ofrecerla significa que el activo esta en el **chequeo de salida** |
| `solicitar_devolucion` (`POST /{id}/solicitar-devolucion`) | Quien tiene el activo (destinatario o responsable actual) | `en_curso` |
| `confirmar_devolucion` (`PUT /{id}/items/{activo_id}/chequeo` y `POST /{id}/confirmar-devolucion`) | Administrador | `en_curso` o `devolucion_solicitada`: el activo esta en el **chequeo de ingreso** |
| `aceptar_acta` (`POST /{id}/actas/{acta_id}/aceptar`) | El destinatario (quien retira o devuelve) | Es del movimiento, no de un item: hay un acta suya pendiente |
| `ejecutar_baja` (`POST /{id}/ejecutar-baja`) | Administrador | Baja `aprobada` |

Aprobar, rechazar y solicitar devolucion aceptan un cuerpo opcional `{activo_ids: [...]}`: sin el, actuan sobre todos los
activos que ese usuario puede; si pide uno que no puede, `403 MOV-007` (o `400 MOV-021` si no es del movimiento).

**Chequeo de salida e ingreso (como una auditoria).** La salida y el ingreso se chequean activo por activo y el
resultado queda guardado en el item (`chequeo_salida` / `chequeo_ingreso`: `{resultado, observacion, por_nombre, fecha}`).
- **Chequear** `PUT /{id}/items/{activo_id}/chequeo` `{resultado: encontrado|con_novedad|no_encontrado, observacion?}`:
  solo administracion (`movimientos-gestionar`). La fase la define el estado del activo (`pendiente_admin` = salida;
  `en_curso` o `devolucion_solicitada` = ingreso). Con novedad la observacion es obligatoria (`400 MOV-023`). Se puede
  corregir hasta cerrar el chequeo. Un activo que no esta en una fase de chequeo, o sin permiso: `403 MOV-028`.
- **Cerrar el chequeo de salida** `POST /{id}/confirmar-salida` `{motivo_no_incluidos?}`: salen los `encontrado` y
  `con_novedad` (el activo pasa a `prestado` y su responsable al destinatario); los `no_encontrado` y los sin chequear
  quedan `rechazado` (etapa `administracion`, con su observacion, o el motivo general, o uno por defecto). Sin ningun
  activo encontrado: `422 MOV-029`. Se genera el **acta de salida** y el movimiento queda `en_curso` esperando el ingreso.
- **Cerrar el chequeo de ingreso** `POST /{id}/confirmar-devolucion` (sin cuerpo): se reciben los `encontrado` y
  `con_novedad` (vuelven a `disponible` y a su responsable original; una novedad queda en el movimiento y como **nota en
  el historial del activo**, `GET /api/activos/{id}/historial`, `tipo: "nota"`). Los `no_encontrado` o sin chequear siguen
  fuera, su marca se limpia y se reciben en otro ingreso. Se genera el **acta de ingreso**.

**Actas** (`actas` en el detalle, en el orden en que se cerraron). Cada una trae `id`, `tipo` (`salida`|`ingreso`),
`numero` (consecutivo por tipo), `fecha_cierre`, `cerrada_por_nombre/correo` (sello del administrador que cerro el
chequeo), `aceptada_por_nombre/correo` y `fecha_aceptacion` (sello del responsable; nulos mientras no acepte), `lineas`
(`activo_id`, nombre, inventario, `resultado`, `observacion`) y `puede_aceptar` (si el usuario con sesion puede aceptarla).
Los sellos llevan **solo nombre y correo**.
- **Aceptar** `POST /{id}/actas/{acta_id}/aceptar`: solo el **destinatario** del movimiento (`403 MOV-027`); una sola vez
  (`409 MOV-026`); acta inexistente `404 MOV-025`. El PDF se vuelve a emitir con los dos sellos y reemplaza al anterior.
- **PDF** `GET /{id}/actas/{acta_id}/pdf`: con la misma visibilidad que el movimiento. `GET /{id}/comprobante` sigue
  existiendo y apunta al PDF vigente del acta de salida mas reciente.
- Cerrar un chequeo avisa por correo a los participantes (pide aceptar el acta) y aceptarla avisa a administracion.
- El cambio sobre los activos no es transaccional: si falla uno se deshacen los ya cambiados y responde
  `422 MOV-011`.

Un item terminal (`rechazado`, `devuelto`, `ejecutado`) no tiene acciones.

**Datos anteriores.** Los movimientos del modelo previo (un activo por movimiento) no son compatibles: en la base de
pruebas se respaldaron en la coleccion `movimientos_v1_respaldo`.

## Identificadores invalidos

Un id que no tiene forma de `ObjectId` (en la ruta, un filtro o el cuerpo) responde `400 GEN-400` en cualquier modulo.
Antes respondia `500 GEN-500`.

## Mantenimientos: acceso exclusivo, locativo, carga masiva y detalle enriquecido

**Acceso exclusivo.** Todo el modulo (listar, ver, descargar archivos, crear, cambiar estado, subir y eliminar archivos,
carga masiva) es solo para los roles `mantenimiento` y `administrador_general`; cualquier otro rol recibe `403`. Antes,
listar, ver y descargar archivos estaba abierto a cualquier usuario con sesion. `POST /verificar-alertas` sigue siendo solo
del administrador.

**Tipos:** `preventivo`, `correctivo` y `locativo` (nuevo). Las ubicaciones codificadas (BAÑO1) y sus elementos
(lavamanos1) son activos de tipo `elemento` con su lugar: un mantenimiento locativo se registra sobre el activo.

**Detalle `GET /api/mantenimientos/{id}`** — ahora trae los nombres (`activo_nombre`, `activo_numero_inventario`,
`tecnico_nombre`), `creado_por_id`, `creado_por_nombre`, `fecha_creacion`, `alerta_enviada` y `estados_permitidos`
(a los que puede pasar ahora: `programado` → `en_proceso`/`cancelado`; `en_proceso` → `completado`/`cancelado`; los
terminales, ninguno). El listado trae lo mismo y `meta.total`. El frontend no debe recalcular los estados.

**Crear `POST /api/mantenimientos`** — ademas de lo anterior:

| Codigo | Cuando |
| --- | --- |
| `MNT-003` | El tecnico no tiene el rol `mantenimiento` **o esta desactivado** |
| `MNT-008` | `solicitud_id` no existe o es de otro activo (una solicitud asociada se resuelve sola al completar el mantenimiento) |

`observaciones` admite hasta 2000 caracteres.

**Carga masiva `POST /api/mantenimientos/masivo`** (decision del responsable: «le realice el mantenimiento a 20 codigos»).
Cuerpo: `codigos` (1 a 200, cada uno de hasta 50 caracteres), `tipo`, `tecnico_responsable_id`, `fecha`, y opcionales
`observaciones`, `costo`, `frecuencia_dias`. Crea **un mantenimiento por codigo, ya `completado`** (el trabajo ya se hizo)
con los mismos datos; con `frecuencia_dias` cada uno calcula su `proxima_fecha_sugerida` y entra a las alertas.

- Los codigos se normalizan como en `activos`: sin espacios y **en mayusculas** (`lavamanos1` encuentra `LAVAMANOS1`);
  se descartan vacios y repetidos (los repetidos no cuentan para el limite).
- Responde `200` con `data: { registrados: [{codigo, activo_id, mantenimiento_id}], no_encontrados: [codigo] }`: registra
  los que existen y lista los que no, aunque ninguno exista (entonces `registrados` va vacio y no se guarda nada).
- Errores: `MNT-009` (sin codigos tras limpiar), `MNT-010` (mas de 200), `MNT-003` (tecnico invalido). La lista vacia, de
  mas de 200 o con un codigo de mas de 50 caracteres la rechaza antes el esquema con `422`.
- El costo, si se indica, se guarda **en cada mantenimiento** (no se reparte).
- La carga no cambia el estado de los activos.

**Alertas.** `POST /verificar-alertas` (solo administrador) avisa de los mantenimientos `completado` cuya
`proxima_fecha_sugerida` cae en los proximos 7 dias y marca `alerta_enviada`. **Nada lo dispara solo todavia** (falta un
planificador) y los avisos solo se escriben en el log hasta que exista el modulo de notificaciones.

## Notificaciones por correo

El sistema avisa por correo (SMTP; sirve para Gmail) y deja constancia de cada intento. Solo el **administrador general**
consulta el historial y administra los envios.

**Quien avisa.** Solicitudes, mantenimientos y movimientos usan el `NotificadorPort` de este modulo
(`modules/notificaciones/infrastructure/composicion.py → get_notificador`). Un aviso **nunca rompe la accion del
usuario**: si el correo falla, se registra y la accion sigue.

**Destinatarios.** Los modulos piden `usuario:<id>`, `rol:<rol>`, `area:<id>` o un correo; el sistema los convierte en
correos de **usuarios activos** (un usuario desactivado no recibe nada), sin repetidos y hasta 200 por aviso.

**Estados de una notificacion:** `enviada`; `fallida` (el servidor de correo respondio con error; queda el detalle);
`omitida` (no habia a quien avisar, o el correo no esta configurado). Cada una cuenta sus `intentos`.

| Endpoint | Quien | Uso |
| --- | --- | --- |
| `GET /api/notificaciones?estado&skip&limit` | Administrador | Historial (con `meta.total`) |
| `GET /api/notificaciones/estado-correo` | Administrador | `{configurado, remitente}`; nunca expone la clave |
| `POST /api/notificaciones/{id}/reenviar` | Administrador | Reintenta una `fallida` u `omitida` (`NTF-002` si ya se envio, `NTF-001` si no existe) |
| `POST /api/notificaciones/procesar-recordatorios` | Administrador **o** Cloud Scheduler | Envia los recordatorios pendientes |

**Cuando se avisa**

| Evento | Destinatarios |
| --- | --- |
| Solicitud creada | El equipo asignado (rol o area) |
| Solicitud cambia de estado | Quien la creo |
| Prestamo o salida solicitados | Cada responsable con activos pendientes de su aprobacion (a administracion le llega cuando ya no falta ninguno) |
| Baja solicitada | Administradores |
| Aprobado por un responsable | Quien lo pidio; y los administradores cuando ya decidieron todos |
| Rechazado (con motivo por activo) / baja aprobada / salida confirmada | Quien lo pidio, quien lo recibe y los responsables originales |
| Devolucion solicitada | Administradores y los participantes |
| Devolucion confirmada (con las novedades) | Quien lo pidio, quien lo recibe y los responsables originales |
| Baja ejecutada | Administradores, participantes y responsable del activo |
| Mantenimiento programado | El tecnico y el responsable del activo |
| Proximo mantenimiento | Rol mantenimiento, responsable y area del activo |
| Recordatorio de devolucion | Quien lo pidio, quien lo tiene y el responsable original |

**Enlaces.** Los correos llevan un enlace a la pagina correspondiente si `APP_URL` esta configurada; sin ella, la linea del
enlace se quita (nunca se manda uno roto). El asunto se limpia a una sola linea (evita inyeccion de cabeceras).

**Recordatorios automaticos.** `procesar-recordatorios` ejecuta dos tareas independientes (si una falla, la otra corre y el
error queda en `errores`): avisar de los proximos mantenimientos (los `completado` con proxima fecha en 7 dias o vencida,
una vez) y **recordar la devolucion** de los movimientos `en_curso` cuya fecha de retorno estimada llega en 1 dia o ya paso
(**una sola vez** por movimiento). Lo dispara Cloud Scheduler: ver `docs/guia_correo_y_recordatorios.md`.

**Acceso del planificador.** Cloud Scheduler envia un token de identidad de Google (OIDC). Se acepta solo si el token es
valido para `GOOGLE_CLOUD_RUN_AUDIENCE`, su correo esta verificado y **es exactamente**
`SCHEDULER_SERVICE_ACCOUNT_EMAIL` (cualquier cuenta de servicio puede pedir un token con esa audiencia: sin comprobar el
correo, cualquiera podria disparar el proceso). Sin esa variable, solo el administrador puede.

**Limites.** Los avisos se envian dentro de la peticion (maximo 15 s de espera al servidor de correo). El historial no
tiene caducidad. Un `omitida` por correo sin configurar se puede reenviar cuando se configure.

## Auditorias

Solo el **administrador general**. Una auditoria toma una fotografia de los activos que tiene asignados un usuario y se
verifica cada uno; al cerrarla se genera un PDF y se envia por correo (con el PDF adjunto).

| Endpoint | Uso |
| --- | --- |
| `POST /api/auditorias` `{usuario_auditado_id}` | Inicia (`AUD-001` si el usuario no existe) |
| `GET /api/auditorias?usuario_auditado_id&estado&creado_por_id&skip&limit` | Listado con `meta.total` y nombres |
| `GET /api/auditorias/{id}` | Detalle con nombres del usuario (`AUD-005` si no existe) |
| `PUT /api/auditorias/{id}/items/{activo_id}` `{resultado, observacion}` | Verifica un item (`AUD-002` si ya esta cerrada, `AUD-003` si el activo no es de la auditoria, `AUD-004` si falta la observacion) |
| `POST /api/auditorias/{id}/cerrar` | Cierra: lo pendiente pasa a `no_encontrado`, genera el PDF y envia el correo |
| `POST /api/auditorias/{id}/reenviar-notificacion` | Reintenta el correo de una auditoria cerrada |
| `GET /api/auditorias/{id}/pdf` | Descarga el reporte (`AUD-006` si no existe) |

Estados: `en_progreso`, `finalizada`, `notificada`, `error_notificacion`. Resultados: `encontrado`,
`encontrado_con_novedad` (observacion **obligatoria**), `no_encontrado`.

**Validaciones.** `observacion` admite hasta 1000 caracteres y se recorta; vacia equivale a sin observacion.
`detalle_error_notificacion` guarda como maximo 300 caracteres del fallo de envio (nunca el stack).

**Respuestas.** El listado y el detalle traen `usuario_nombre`, `usuario_identificacion` y `usuario_email`; las respuestas de
iniciar, verificar, cerrar y reenviar **no** (solo `usuario_auditado_id`): el cliente conserva los que ya tiene.

**Correo.** Usa su propio envio SMTP con el PDF adjunto; **no** queda en el historial de `notificaciones`. El estado y el motivo
del fallo se ven en la auditoria.


## Permisos por rol y Super administrador

Las funciones que cada rol puede usar **ya no estan escritas en el codigo**: viven en la coleccion `permisos_rol` y las
edita el **Super administrador** (rol nuevo `super_administrador`, por encima del Administrador General).

**Autorizacion de rutas.** Cada ruta exige `requiere_permiso("<modulo>-<accion>")` (en
`shared/infrastructure/api/dependencies/user_authentication.py`). El catalogo y la matriz de fabrica estan en
`shared/domain/permisos.py`; la matriz de fabrica reproduce lo que cada rol podia hacer antes. `requiere_rol(...)` se
conserva, pero el Super administrador pasa cualquier guardia. Una clave que no esta en el catalogo falla al arrancar.

- El Super administrador **siempre** tiene todo y no se edita. Las funciones base (`home-ver`, `cuenta-ver`) no se pueden quitar a ningun rol.
- La matriz se lee de Mongo con una cache de 5 s que se vacia al guardar: un cambio rige en el backend de inmediato.
- Reglas que dependen de una funcion sin cortar toda la ruta usan `tiene_permiso(rol, clave)`:
  `movimientos-baja` (pedir una baja), `movimientos-destinatario` (elegir a otra persona como destinatario) y
  `mantenimientos-tecnico` (asignar un tecnico distinto de uno mismo).
- Las rutas de lectura de catalogos, `GET /api/usuarios/directorio`, `/me` y la contrasena propia solo piden sesion.
- **Un Administrador General no puede ascenderse ni gestionar a un Super administrador** (`USR-013`, 403): crear/editar/
  desactivar/reactivar/restablecer sobre ese rol exige ser Super administrador.
- Los avisos dirigidos a "el administrador" (movimientos) llegan al Administrador General y al Super administrador.

**Sesion.** `POST /api/usuarios/login/google`, `POST /api/usuarios/login` y `GET /api/usuarios/me` devuelven ademas
`permisos`: la lista de funciones habilitadas para su rol (el Super administrador recibe tambien `administracion-ver`).

**Endpoints** (todos solo del Super administrador):

| Endpoint | Uso |
| --- | --- |
| `GET /api/permisos/matriz` | Catalogo de funciones (`clave`, `modulo`, `etiqueta`, `descripcion`, `es_base`) y, por rol, `permisos` y `editable` |
| `PUT /api/permisos/roles/{rol}` `{permisos: [...]}` | Deja exactamente esas funciones habilitadas (`PER-003` funcion inexistente, `PER-004` quitar una base, `PER-002` rol no editable, `PER-001` rol inexistente) |
| `POST /api/permisos/roles/{rol}/restablecer` | Devuelve el rol a la matriz de fabrica |
| `GET /api/permisos/historial?rol&skip&limit` | Cambios (habilitado/deshabilitado, quien y cuando), del mas reciente al mas antiguo |

**Datos.** `permisos_rol` (un documento por rol editable, indice unico `uq_rol`) y `permisos_historial` (una entrada por
funcion cambiada). Al arrancar se crea la matriz de fabrica de los roles que aun no tienen documento; nunca pisa lo editado.
