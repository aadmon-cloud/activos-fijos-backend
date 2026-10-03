# Flujo de trabajo — Módulo nuevo con Claude

Cómo construir un módulo desde cero correctamente.
**Regla de oro: no avanzar a la siguiente fase sin aprobar la anterior.**

---

## Fase 0 — Definición de alcance

El desarrollador describe el requerimiento. Claude hace preguntas hasta poder responder:

| Pregunta | Por qué importa |
|---|---|
| ¿Cuál es la entidad principal? | Define el límite del módulo |
| ¿Qué campos son obligatorios desde el día uno? | Evita migraciones innecesarias |
| ¿Tiene estados? ¿Cuáles? ¿Transiciones válidas? | Decide si necesita historial |
| ¿Qué servicios incluye este alcance? (lista concreta) | Evita scope creep durante la construcción |
| ¿Con qué otros módulos se relaciona? | Define referencias y desnormalización |
| ¿Hay algo en `shared/` que ya resuelva parte del problema? | Evita duplicar lógica transversal |

**Salida:** alcance escrito y acordado antes de continuar.

---

## Fase 1 — Modelado MongoDB

Con el alcance claro, diseñar la colección **antes de escribir código**,
usando `.claude/MONGODB_MODELING.md` como guía:

1. Estructura del documento (campos, tipos, obligatorios/opcionales)
2. Qué se embebe y qué se referencia (con justificación)
3. Patrón de auditoría (`creado_por` / `actualizado_por`)
4. Historial de estados (si aplica)
5. Índices para las consultas principales

El desarrollador valida el modelo propuesto por escrito antes de continuar.

**Salida:** schema confirmado (estructura + índices). No hay código hasta aquí.

---

## Fase 2 — Diseño de dominio y servicios

Con el schema aprobado, Claude propone:

1. Entidad de dominio — campos, tipos
2. Puerto de repositorio — métodos abstractos necesarios
3. Lista de servicios — nombre, input, output, reglas de negocio
4. Errores de dominio posibles

Claude presenta el diseño completo para revisión. **Aún no escribe código.**

**Salida:** plan aprobado por el desarrollador.

---

## Fase 3 — Construcción

Con el plan aprobado, construir siguiendo el orden de `.claude/TEMPLATE.md`:

```
domain/         ← entidad + errores
application/    ← DTOs + puerto + servicios + tests
infrastructure/ ← repositorio + rutas + dependencies
bootstrap.py    ← register_module()
```

Tests unitarios se escriben junto a cada servicio, no al final.

---

## Fase 4 — Cierre (antes del PR)

Recorrer `.claude/SOLID_CHECKLIST.md` completo.

---

## Referencia rápida

| Fase | Archivo de apoyo |
|---|---|
| Modelado Mongo | `.claude/MONGODB_MODELING.md` |
| Construcción de consultas | `.claude/MONGODB_QUERIES.md` |
| Estructura de archivos | `.claude/TEMPLATE.md` |
| Checklist pre-PR | `.claude/SOLID_CHECKLIST.md` |
| Convenciones de nombres | `.claude/CONVENTIONS.md` |
