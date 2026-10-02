# MongoDB — Construcción de consultas y pipelines

---

## Orden canónico de un pipeline

```
1. $match          ← reducir documentos lo antes posible
2. $sort           ← soportado por índice, antes de paginar
3. $lookup         ← solo si ya se redujo el conjunto
4. $addFields      ← enriquecer después del cruce
5. $project        ← recortar campos innecesarios
6. .paginar()      ← siempre al final (llama $facet internamente)
```

La regla de oro: **cada etapa recibe menos documentos que la anterior**.

---

## $match — reglas

### 1. Siempre al inicio, lo más pronto posible

```python
# MAL: match después de un lookup innecesario
.agregar({"$lookup": {...}})           # cruza toda la colección
.agregar({"$match": {"estado": "activo"}})  # filtra tarde

# BIEN: filtrar antes del cruce
.agregar({"$match": {"estado": "activo"}})
.agregar({"$lookup": {...}})
```

### 2. Agrupar condiciones en un solo $match

Varios `$match` seguidos incondicionales se fusionan internamente en Mongo, pero son difíciles de leer y razonar. Si las condiciones siempre aplican juntas, construirlas en un solo dict:

```python
# MAL: tres $match seguidos para la misma consulta
.agregar({"$match": {"id_proyecto": ObjectId(id_proyecto)}})
.agregar({"$match": {"numero_item": numero_item}})
.agregar({"$match": {"id_categoria": {"$in": ids_categorias}}})

# BIEN: un solo $match con todas las condiciones
match: dict = {
    "id_proyecto": ObjectId(id_proyecto),
    "numero_item": numero_item,
    "id_categoria": {"$in": ids_categorias},
}
if fecha_desde:
    match["fecha"] = {"$gte": fecha_desde}
if fecha_hasta:
    match.setdefault("fecha", {})["$lte"] = fecha_hasta
.agregar({"$match": match})
```

### 3. $match condicionales encadenados — cuándo es aceptable

Está bien tener métodos separados que cada uno agrega su propio `$match` cuando **cada condición es opcional** y el builder los acumula solo si el parámetro viene:

```python
# Aceptable: cada método solo agrega el $match si el parámetro viene
builder.filtrar_por_estado(estado)      # agrega $match solo si estado != None
       .filtrar_por_categoria(cat)      # agrega $match de categoría
       .buscar_texto(q)                 # agrega $match de regex solo si q != ""
```

El problema aparece cuando se apilan `$match` que **siempre se ejecutan** sobre los mismos campos — ahí conviene fusionarlos.

---

## $sort — reglas

### 1. Siempre respaldado por un índice

Un `$sort` sin índice hace un sort en memoria sobre todos los documentos que llegaron hasta ese punto. Si el conjunto es grande, es costoso.

```python
# idx_id_proyecto_fecha: (id_proyecto, fecha DESC) existe en la colección
.agregar({"$match": {"id_proyecto": ObjectId(id_proyecto)}})   # usa el índice
.agregar({"$sort": {"fecha": -1, "_id": -1}})                  # continúa por índice
```

### 2. Sort antes de $lookup y $project

Sort sobre campos del documento principal es más barato que sort después de un enriquecimiento.

### 3. Sort estable para paginación consistente

Siempre incluir `_id` como campo de desempate para resultados reproducibles entre páginas:

```python
{"$sort": {"fecha": -1, "_id": -1}}   # estable
{"$sort": {"fecha": -1}}               # puede cambiar entre páginas si hay empates
```

El método `paginar()` del pipeline base lo hace automáticamente si no hay sort previo.

---

## $lookup — dos formas

### Forma simple (evitar si la colección es grande o hay campos innecesarios)

```python
{"$lookup": {
    "from": "usuarios",
    "localField": "id_usuario",
    "foreignField": "_id",
    "as": "_usuario",
}}
```

Trae **todos los campos** de cada documento de `usuarios`. Aceptable solo si la colección es pequeña o realmente necesitas todos los campos.

### Forma con pipeline interno (preferida)

Permite filtrar y proyectar **dentro del lookup**, antes de que los documentos cruzados lleguen al documento padre. Trae solo lo necesario:

```python
{"$lookup": {
    "from": "usuarios",
    "let": {"ids": "$items.id_usuario"},      # variables del doc principal
    "pipeline": [
        {"$match": {"$expr": {"$in": ["$_id", "$$ids"]}}},  # filtro dentro del lookup
        {"$project": {"foto_perfil": 1}},                    # solo el campo necesario
    ],
    "as": "_usuarios",
}}
```

**Usar pipeline interno cuando:**
- La colección cruzada es grande
- Solo necesitas 1–3 campos del documento cruzado
- Necesitas filtrar dentro del lookup antes de cruzar (condición adicional más allá del join)

### Limpiar campos temporales del lookup

Los campos intermedios del lookup (`_usuarios`, `_roles`, `_sitios`) deben eliminarse al final con `$project`:

```python
.agregar({"$project": {"_usuarios": 0}})   # elimina el campo temporal
```

O incluirlos en el `$project` final sin mencionarlos (solo proyectar lo que sí necesitas).

### Filtrar ANTES del $lookup

Si puedes reducir los documentos con un `$match` antes del `$lookup`, hazlo siempre:

```python
# MAL: lookup sobre toda la colección, luego filtrar
.agregar({"$lookup": {"from": "usuarios", ...}})
.agregar({"$match": {"estado": "activo"}})

# BIEN: reducir primero, luego cruzar
.agregar({"$match": {"estado": "activo"}})
.agregar({"$lookup": {"from": "usuarios", ...}})
```

---

## $project — reglas

### 1. Proyectar pronto para reducir el tamaño de documentos

En listados, proyectar solo los campos del resumen antes de paginar:

```python
.agregar({"$sort": {"fecha": -1, "_id": -1}})
.proyectar_resumen()    # reduce campos antes del $facet
.paginar(pagina, limite)
```

### 2. Calcular campos derivados en el $project

En lugar de traer arrays completos y calcularlos en Python, calcular en Mongo:

```python
"$project": {
    "total_items": {"$size": "$items"},          # en lugar de len(doc["items"])
    "total_activos": {
        "$size": {
            "$filter": {
                "input": "$items",
                "as": "i",
                "cond": {"$eq": ["$$i.activo", True]},
            }
        }
    },
}
```

### 3. Usar $ifNull para campos opcionales

Evitar que un campo nulo rompa el mapeo:

```python
"nombre": {"$ifNull": ["$$r.nombre", ""]}
```

---

## Paginación — siempre con `.paginar()`

El método base en `ConstructorPipelineBase.paginar()` implementa el patrón estándar:
`$facet` → `$project` → `$addFields` con metadata.

Reglas:
- Llamar siempre **al final** del pipeline, después del `$project` de resumen
- El `$sort` debe ir **antes** de llamar a `paginar()` — si no hay sort, el método agrega `{_id: 1}` automáticamente para estabilidad
- No implementar paginación manual con `$skip`/`$limit` fuera de `paginar()`

```python
pipeline = (
    ListarXxxPipelineBuilder()
    .filtrar_por_estado(estado)
    .filtrar_por_categoria(cat)
    .buscar_texto(q)
    .proyectar_resumen()        # reducir antes de paginar
    .paginar(pagina, limite)    # siempre al final
)
```

---

## Anti-patrones

| Anti-patrón | Problema | Solución |
|---|---|---|
| `$lookup` sin pipeline interno sobre colección grande | Trae todos los campos de todos los docs cruzados | Usar forma `let/pipeline` con `$project` interno |
| `$sort` sin índice sobre muchos documentos | Sort en memoria, costoso | Asegurar que el campo tenga índice |
| `$match` después de `$lookup` sobre campo del doc principal | El lookup ya procesó más docs de los necesarios | Mover el `$match` antes del `$lookup` |
| Múltiples `$match` seguidos incondicionales | Difícil de razonar, aunque Mongo los fusiona | Construir un solo dict de condiciones |
| `$skip`/`$limit` directo sin `$facet` | No devuelve el total, no se puede paginar correctamente | Usar `.paginar()` |
| Calcular longitud de arrays en Python después de la consulta | Trae el array entero por red | Usar `{"$size": "$campo"}` en `$project` |
| No limpiar campos temporales del `$lookup` (`_usuarios`, `_roles`) | Ensucian la respuesta si no hay `$project` final | Agregar `{"$project": {"_campo_temp": 0}}` |
