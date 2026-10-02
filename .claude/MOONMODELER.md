# Moon Modeler — modelado visual de MongoDB

Moon Modeler es la herramienta visual de referencia para diseñar las colecciones antes de escribir código. El modelo vive en `docs/mongo/moonmodeler/` como archivo `.dmm` (JSON).

**Regla:** no escribir código de infraestructura hasta que el modelo esté aprobado visualmente.

---

## Cuándo usar Moon Modeler

- Al diseñar una colección nueva (Fase 1 del WORKFLOW.md)
- Al agregar subdocumentos o cambiar relaciones significativamente
- Para documentar la estructura final del schema en el repositorio

---

## Alternativas aceptables

Si el proyecto no usa Moon Modeler, cualquier herramienta visual es válida (dbdiagram.io, Whimsical, draw.io). Lo importante es que el modelo esté acordado antes de implementar.

---

## Estructura del archivo .dmm (para referencia)

El `.dmm` es JSON con esta forma:

```json
{
  "tables":    { "<uuid>": tabla },
  "relations": { "<uuid>": relación },
  "model":     { "activeDiagram": "<uuid>" },
  "diagrams":  { "<uuid>": { "diagramItems": { "<uuid tabla>": item } } }
}
```

Reglas clave:
- **Colección** = tabla con `visible: true`, `embeddable: false`, primary key sobre `_id`
- **Objeto embebido** = tabla con `visible: false`, `embeddable: true`
- Tipos escalares: `objectId`, `string`, `int`, `date`, `bool`, `enum`
- **No editar el JSON a mano** si el proyecto usa los helpers de scripts — los UUIDs cruzados hacen fácil corromperlo

---

## Script driver (si el proyecto tiene helpers)

Si el proyecto incluye `scripts/mongo/dmm_helpers.py`, usar un script driver temporal:

```python
import sys
sys.path.insert(0, "scripts/mongo")
from dmm_helpers import *

PATH = r"docs/mongo/moonmodeler/DbModel.dmm"
data = load_dmm(PATH)

# objeto embebido de auditoría
cre_cols = [
    col("id_usuario", "objectId", nn=True, fk=True),
    col("nombre", "string", nn=True, fk=False),
    col("fecha", "date", nn=True, fk=False),
]
cre = table("object", cre_cols, visible=False, keys=[empty_pk()])

# colección nueva
tid = col("_id", "objectId", nn=True, pk=True)
nueva = table("mi_coleccion", [
    tid,
    col("titulo", "string", nn=True),
    col("estado", "enum", nn=True, enum='["borrador", "activo"]'),
    col("creado_por", cre["id"], nn=True, fk=False),
], visible=True, keys=[pk_key(tid["id"])])

add_tables(data, [nueva, cre])
set_diagram_position(data, nueva["id"], x=700, y=700, gh=300, gw=260, bg="#03a9f4")

verify(data)
save_dmm(data, PATH)
```

Procedimiento:
1. Escribir el driver temporal (p. ej. `tmp_dmm.py` en la raíz)
2. Ejecutar `python tmp_dmm.py` y validar
3. Revisar el resultado visual en Moon Modeler
4. Borrar el driver temporal

---

## Lo que NO modela el .dmm

Los índices no se modelan en el `.dmm` — viven en `infrastructure/persistence/mongo/schema/` de cada módulo. Anotar índices únicos importantes en el `desc` de la colección como referencia.
