# MongoDB — Construcción de consultas y pipelines

## Alcance de esta plantilla

Esta plantilla no incluye un helper tipo `ConstructorPipelineBase`/`.paginar()`
para construir pipelines de agregación — el módulo de ejemplo `tareas` usa
consultas simples (`find().sort()`) porque no las necesita. Las convenciones
de esta página son la guía de referencia para cuando un módulo sí requiera
pipelines de agregación complejos; si la necesidad se repite entre módulos,
portar el helper desde `ms-continuum` como adición deliberada a `shared/`.

---

## Orden canónico de un pipeline

```
1. $match          ← reducir documentos lo antes posible
2. $sort           ← soportado por índice, antes de paginar
3. $lookup         ← solo si ya se redujo el conjunto
4. $addFields      ← enriquecer después del cruce
5. $project        ← recortar campos innecesarios
6. paginación      ← siempre al final
```

La regla de oro: **cada etapa recibe menos documentos que la anterior**.

## $match — reglas

1. Siempre al inicio, lo más pronto posible.
2. Agrupar condiciones en un solo `$match` cuando siempre aplican juntas.
3. Métodos separados que cada uno agrega su propio `$match` condicional son aceptables cuando cada condición es opcional.

## $sort — reglas

1. Siempre respaldado por un índice.
2. Sort antes de `$lookup` y `$project`.
3. Sort estable: incluir `_id` como desempate para paginación consistente.

## $lookup — dos formas

- **Forma simple**: trae todos los campos del documento cruzado. Aceptable solo si la colección es pequeña.
- **Forma con pipeline interno** (preferida): filtra y proyecta dentro del `$lookup`, trae solo lo necesario. Usar cuando la colección cruzada es grande o solo necesitas 1-3 campos.
- Filtrar **antes** del `$lookup` siempre que se pueda.
- Limpiar campos temporales del lookup (`_personas`, `_roles`) con `$project` al final.

## $project — reglas

1. Proyectar pronto para reducir el tamaño de documentos.
2. Calcular campos derivados en el `$project` (`$size`, `$filter`) en vez de en Python.
3. Usar `$ifNull` para campos opcionales.

## Anti-patrones

| Anti-patrón | Problema | Solución |
|---|---|---|
| `$lookup` sin pipeline interno sobre colección grande | Trae todos los campos de todos los docs cruzados | Usar forma `let/pipeline` con `$project` interno |
| `$sort` sin índice sobre muchos documentos | Sort en memoria, costoso | Asegurar que el campo tenga índice |
| `$match` después de `$lookup` sobre campo del doc principal | El lookup ya procesó más docs de los necesarios | Mover el `$match` antes del `$lookup` |
| Múltiples `$match` seguidos incondicionales | Difícil de razonar | Construir un solo dict de condiciones |
| Calcular longitud de arrays en Python después de la consulta | Trae el array entero por red | Usar `{"$size": "$campo"}` en `$project` |
