# API — Módulo de <Nombre>

> Plantilla del formato estándar de documentación API para frontend.
> Una guía por módulo en `docs/api/<MODULO>.md`, escrita al cerrar la Fase 3 del workflow.
> Swagger (`/docs`) es el contrato vivo; esta guía aporta lo que Swagger no cuenta:
> flujos, reglas de negocio, semántica de errores y ejemplos realistas.

**Base:** `/api/<modulo>` · **Auth:** Bearer token

Párrafo breve: qué hace el módulo y qué problema resuelve para el usuario final.

---

## 1. Convenciones de respuesta

Envelope de éxito/error y tabla `categoría → HTTP` (copiar de un módulo existente —
son globales del sistema). Estructura de paginación si el módulo lista.

## 2. Tipos y enums

Tabla de enums con sus valores exactos (en minúsculas, como viajan por la API) y
ejemplos JSON de los objetos compuestos que el front tiene que construir o renderizar.

## 3. Flujos

Los recorridos principales en 2–5 líneas cada uno (uno por tipo de actor), señalando
con ⚠️ los puntos de no retorno (bloqueos, estados finales, acciones únicas).

## 4..N. Endpoints (agrupados por actor o capacidad)

Por endpoint:

### MÉTODO `/api/ruta` — qué hace · permiso `permiso-requerido`

- Query params / body de ejemplo (JSON realista, con comentarios `//` donde aclare)
- Respuesta de ejemplo (el `data`, no el envelope completo)
- Errores posibles con código de dominio y HTTP, y cuándo ocurre cada uno

## Catálogo de errores

| Código | HTTP | Significado | Acción sugerida en UI |
|---|---|---|---|

Todos los códigos `XXX-nnn` del módulo. La columna de acción sugerida es lo que más
valor le da al front: qué hacer cuando recibe ese error.

## Notas de comportamiento

Reglas transversales que no pertenecen a un endpoint puntual: comportamientos
automáticos, privacidad, formatos de fecha, alcance futuro / fuera de alcance.
