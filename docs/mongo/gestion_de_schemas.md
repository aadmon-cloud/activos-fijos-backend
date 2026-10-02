# Guia de Gestion de Schemas Mongo

## Objetivo

Este documento explica como administrar validadores e indices de MongoDB dentro del proyecto.

La idea es que el equipo tenga una fuente clara para:

- saber donde definir una coleccion
- entender como registrar nuevos schemas
- ejecutar el sincronizador de Mongo de forma segura
- distinguir entre validadores, indices y migraciones de datos

## Alcance

Esta guia cubre:

- validadores de coleccion (`validator` / `$jsonSchema`)
- indices declarados por el proyecto
- sincronizacion manual o automatizada desde un script

Esta guia no cubre:

- migraciones de datos historicas
- refactors de documentos ya persistidos
- decisiones de modelado funcional, que siguen documentadas en [modelado_y_consultas.md](docs/mongo/modelado_y_consultas.md)

## Estructura actual

Actualmente el proyecto usa esta estructura:

```text
docs/
  mongo/
    moonmodeler/
    gestion_de_schemas.md
    modelado_y_consultas.md

scripts/
  mongo/
    sync_schema.py

shared/
  infrastructure/
    persistence/
      mongo/
        schema/
          definitions.py
          registry.py
          runner.py

modules/
  organizaciones/
    infrastructure/
      persistence/
        mongo/
          schema/
            organizaciones_collection.py
  personas/
    infrastructure/
      persistence/
        mongo/
          schema/
            personas_collection.py
  proyectos/
    infrastructure/
      persistence/
        mongo/
          schema/
            proyectos_collection.py
  tareas/
    infrastructure/
      persistence/
        mongo/
          schema/
            tareas_collection.py
```

### Que va en cada lugar

- `docs/mongo/moonmodeler/`
  - archivos de Moon Modeler y artefactos documentales
- `shared/infrastructure/persistence/mongo/schema/definitions.py`
  - contratos declarativos para colecciones e indices
- `shared/infrastructure/persistence/mongo/schema/runner.py`
  - motor que aplica validators e indices en MongoDB
- `shared/infrastructure/persistence/mongo/schema/registry.py`
  - registro central de colecciones administradas
- `modules/<modulo>/infrastructure/persistence/mongo/schema/`
  - definiciones concretas de las colecciones de cada modulo
- `scripts/mongo/sync_schema.py`
  - comando ejecutable para sincronizar el schema

## Regla de ubicacion

La definicion versionada de una coleccion debe vivir en el modulo dueno de esa coleccion:

```text
modules/<modulo>/infrastructure/persistence/mongo/schema/
```

Ejemplos actuales:

- `modules/organizaciones/infrastructure/persistence/mongo/schema/organizaciones_collection.py`
- `modules/personas/infrastructure/persistence/mongo/schema/personas_collection.py`
- `modules/proyectos/infrastructure/persistence/mongo/schema/proyectos_collection.py`
- `modules/tareas/infrastructure/persistence/mongo/schema/tareas_collection.py`

`shared/infrastructure/persistence/mongo/schema/` se reserva para infraestructura comun del mecanismo de schemas, no para definir colecciones de negocio.

## Como definir una coleccion

Cada coleccion debe definirse como una constante de tipo `MongoCollectionDefinition`.

La estructura general es esta:

```python
from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)

MI_COLECCION = MongoCollectionDefinition(
    name="mi_coleccion",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["campo_obligatorio"],
            "properties": {
                "campo_obligatorio": {"bsonType": "string"},
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="idx_mi_coleccion_campo_obligatorio",
            keys=[("campo_obligatorio", 1)],
        ),
    ],
)
```

## Como registrar una coleccion nueva

Despues de crear el archivo de definicion, se debe registrar en [registry.py](shared/infrastructure/persistence/mongo/schema/registry.py).

Ejemplo:

```python
from modules.mi_modulo.infrastructure.persistence.mongo.schema.mi_coleccion import (
    MI_COLECCION,
)


def obtener_colecciones_mongo() -> list[MongoCollectionDefinition]:
    return [
        ORGANIZACIONES_COLLECTION,
        PERSONAS_COLLECTION,
        PROYECTOS_COLLECTION,
        TAREAS_COLLECTION,
        MI_COLECCION,
    ]
```

Si una coleccion no esta en el registro, el sincronizador no la vera.

## Flujo recomendado

El flujo esperado del equipo es:

1. Modelar la coleccion en Moon Modeler.
2. Revisar el modelo y sus consultas principales.
3. Crear la definicion Python del schema dentro del modulo dueno.
4. Declarar validator e indices.
5. Registrar la coleccion en `registry.py`.
6. Ejecutar primero un `dry-run`.
7. Revisar logs, warnings e indices.
8. Ejecutar la sincronizacion real.

## Como ejecutar el sincronizador

El comando actual es:

```powershell
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema
```

Tambien puedes correrlo con opciones:

```powershell
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --dry-run
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --only proyectos
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --dry-run --drop-extra-indexes
```

### Significado de cada opcion

- `--dry-run`
  - muestra que haria sin aplicar cambios
  - no crea colecciones
  - no ejecuta `collMod`
  - no crea indices
  - no elimina indices extra
- `--only <colecciones>`
  - limita la ejecucion a una o varias colecciones
- `--drop-extra-indexes`
  - elimina indices existentes que no esten declarados en el schema

## Que hace el sincronizador

El sincronizador sigue este comportamiento:

### Si la coleccion no existe

- crea la coleccion
- aplica el `validator`
- crea los indices declarados

En `--dry-run`:

- no crea la coleccion
- solo reporta que la crearia

### Si la coleccion ya existe

- ejecuta `collMod`
- actualiza el `validator`
- revisa los indices declarados
- crea los indices faltantes

En `--dry-run`:

- no ejecuta `collMod`
- no crea indices
- solo reporta lo que actualizaria o crearia

### Si un indice declarado ya existe con la misma definicion

- no hace nada
- lo reporta como indice sin cambios

### Si un indice declarado ya existe con una definicion distinta

- no lo reemplaza automaticamente
- genera un `warning`
- requiere revision manual

### Si existen indices extra en Mongo

Sin `--drop-extra-indexes`:

- no los elimina
- los reporta como `warning`

Con `--drop-extra-indexes`:

- planea eliminarlos
- en `--dry-run` solo informa
- sin `--dry-run` si los elimina

Importante:

- `--dry-run --drop-extra-indexes` no modifica MongoDB
- ese comando solo muestra que indices extra se eliminarian
- para aplicar los cambios, se debe ejecutar luego sin `--dry-run`

### Indice `_id_`

El indice `_id_` nunca se elimina.

## Que no hace este mecanismo

Este sistema no reemplaza las migraciones de datos.

Ejemplos de cosas que no resuelve por si solo:

- transformar documentos viejos a una estructura nueva
- poblar campos faltantes en millones de registros
- recalcular valores derivados
- mover datos entre colecciones

Para eso se deben crear scripts o jobs de migracion separados.

## Cuando debe ejecutarse

No se recomienda ejecutar el sincronizador en el arranque de FastAPI.

La practica recomendada es ejecutarlo:

- manualmente en desarrollo
- en un paso de despliegue
- o en un Cloud Run Job antes de desplegar la API

Flujo recomendado:

```text
build/deploy
-> sync_schema
-> deploy del servicio
```

## Permisos necesarios

La identidad que ejecute este script en MongoDB debe poder hacer operaciones equivalentes a:

- listar colecciones
- crear colecciones
- modificar colecciones con `collMod`
- listar indices
- crear indices
- eliminar indices, si se usa `--drop-extra-indexes`

En Atlas con autenticacion X.509, estos permisos deben existir en el usuario o rol asociado al certificado.

## Convenciones recomendadas

### Nombres de archivos

- `proyectos_collection.py`
- `organizaciones_collection.py`
- `personas_collection.py`
- `tareas_collection.py`

### Nombres de constantes

- `PROYECTOS_COLLECTION`
- `ORGANIZACIONES_COLLECTION`
- `PERSONAS_COLLECTION`
- `TAREAS_COLLECTION`

### Nombres de indices

Usar nombres explicitos y estables:

- `uq_proyectos_consecutivo`
- `idx_proyectos_estado`
- `idx_organizaciones_nit`

Regla practica:

- `uq_` para indices unicos
- `idx_` para indices no unicos

## Checklist antes de agregar una coleccion

- Ya existe el modelo en Moon Modeler
- La coleccion ya tiene modulo dueno
- El archivo del schema quedo en `modules/<modulo>/infrastructure/persistence/mongo/schema/`
- El `validator` refleja el contrato minimo del documento
- Los enums estan completos y correctos
- Los indices responden a consultas reales
- La coleccion quedo registrada en `registry.py`
- Probaste primero con `--dry-run`

## Regla final

Los schemas Mongo del proyecto deben tratarse como codigo versionado.

Eso significa:

- se revisan en PR
- viven en el repositorio
- se ejecutan con un flujo controlado
- no se administran solo desde la consola de Mongo ni solo desde Moon Modeler
