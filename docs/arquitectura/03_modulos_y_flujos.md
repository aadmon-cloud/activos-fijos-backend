# Modulos y flujos

## Modulos funcionales

### `organizaciones`

- Lista el catalogo de organizaciones.
- Endpoint principal: `GET /api/organizaciones`

### `personas`

- Lista personas y permite filtrar por `organizacion_id`.
- Endpoint principal: `GET /api/personas`

### `proyectos`

- Administra proyectos y su equipo.
- Incluye crear, consultar, actualizar, cambiar estado y gestionar miembros.
- `GET /api/proyectos` requiere `persona_id_consulta` para resolver alcance.

### `tareas`

- Administra tareas, comentarios y registros de trabajo.
- Incluye listados personales como `mis-asignadas` y `mis-proyectos`.
- Los listados personales requieren `persona_id_consulta`.

## Flujo tipico de una solicitud

```text
HTTP request
-> route FastAPI
-> dependency provider
-> application service
-> repository port
-> mongo repository
-> response schema
```

## Donde buscar segun el tipo de cambio

- Endpoint nuevo en un modulo existente:
  `modules/<modulo>/infrastructure/api/`
- Regla de negocio nueva:
  `modules/<modulo>/domain/` o `application/services/`
- Cambio de persistencia:
  `modules/<modulo>/infrastructure/persistence/mongo/`
- Cambio transversal:
  `shared/`

## Puntos de ensamblaje importantes

- Registro global de modulos: `shared/bootstrap/application.py`
- Entrada del servicio: `main.py`
- Dependencias HTTP compartidas: `shared/infrastructure/api/dependencies/`
