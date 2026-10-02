# Manual de Mongo: Modelado, Validadores e Indices

## Objetivo de este documento

Este manual define la forma recomendada de trabajar con MongoDB en el proyecto.

Su objetivo es que, antes de crear una coleccion o consulta nueva, el equipo piense primero en:

- el modelo de informacion
- el crecimiento de los datos en el tiempo
- los validadores de la coleccion
- los indices y llaves unicas
- la forma correcta de construir pipelines

Este documento complementa el manual de arquitectura hexagonal y se enfoca en el diseno de persistencia Mongo. La parte operativa de donde declarar y como sincronizar schemas vive en [gestion_de_schemas.md](docs/mongo/gestion_de_schemas.md).

## Regla principal

Antes de crear una coleccion nueva o un repositorio Mongo nuevo, primero se debe modelar la informacion.

El flujo recomendado es:

1. Analizar la necesidad funcional del modulo.
2. Disenar la coleccion en Moon Modeler.
3. Validar como podria crecer la informacion en volumen, cardinalidad y relaciones.
4. Definir validator, indices y restricciones a partir del modelo aprobado.
5. Crear la definicion del schema en `modules/<modulo>/infrastructure/persistence/mongo/schema/`.
6. Registrar la coleccion en `shared/infrastructure/persistence/mongo/schema/registry.py`.
7. Implementar el repositorio y los pipelines.
8. Ejecutar la sincronizacion del schema.

## Modelado de colecciones

Cada vez que se cree un modulo nuevo y se requiera una coleccion nueva, esta debe modelarse primero.

Reglas:

- la coleccion debe visualizarse primero en Moon Modeler
- el modelo debe revisarse antes de escribir codigo
- el diseno debe considerar el crecimiento futuro de los datos
- se debe decidir explicitamente que campos son obligatorios, opcionales y cuales pueden cambiar con el tiempo

Preguntas que deben responderse antes de crear la coleccion:

- Cual es el identificador natural y cual es el identificador tecnico
- Que campos son obligatorios desde el dia uno
- Que campos pueden crecer mucho con el tiempo
- Que relaciones conviene embeber y cuales conviene referenciar
- Que consultas se haran con mayor frecuencia
- Que filtros y ordenamientos necesitan soporte eficiente
- Hay campos que deban ser unicos

### Sobre identificador natural e identificador tecnico

Esta distincion ayuda a decidir llaves, validadores, consultas e indices.

- identificador tecnico: el identificador interno que usa el sistema para persistencia y relaciones
- identificador natural: un valor del negocio que por su naturaleza identifica al registro

Ejemplos:

- tecnico:
  - `_id` de Mongo
  - `uuid`
  - `id` generado por el sistema
- natural:
  - correo electronico
  - numero de documento
  - codigo de producto
  - placa de vehiculo
  - una combinacion como `tipo_documento + numero_documento`
  - un consecutivo de negocio como `consecutivo`

Regla recomendada:

- casi siempre tener un identificador tecnico propio
- analizar si tambien existe un identificador natural que deba indexarse o declararse como unico

## Del modelo grafico al schema versionado

Moon Modeler es la fuente de modelado visual, pero no reemplaza la definicion versionada del proyecto.

Una vez aprobado el modelo:

1. Se crea la definicion Python de la coleccion en el modulo dueno.
2. Se declaran validator e indices usando `MongoCollectionDefinition`.
3. Se registra la coleccion en [registry.py](shared/infrastructure/persistence/mongo/schema/registry.py).
4. Se sincroniza Mongo con el script del proyecto.

En el estado actual del repositorio, las definiciones viven en rutas como estas:

- `modules/organizaciones/infrastructure/persistence/mongo/schema/organizaciones_collection.py`
- `modules/personas/infrastructure/persistence/mongo/schema/personas_collection.py`
- `modules/proyectos/infrastructure/persistence/mongo/schema/proyectos_collection.py`
- `modules/tareas/infrastructure/persistence/mongo/schema/tareas_collection.py`

## Validadores de coleccion

Una vez aprobado el modelo, se debe definir un validator para la coleccion.

Objetivos del validator:

- proteger la integridad minima de los documentos
- evitar estructuras inconsistentes
- hacer explicitas las reglas basicas del contrato de datos

Reglas:

- el validator debe salir del modelo ya analizado, no improvisarse sobre la marcha
- debe validar estructura, tipos y campos obligatorios
- no debe reemplazar todas las validaciones de negocio del dominio
- debe actuar como una barrera tecnica de consistencia

En otras palabras:

- el dominio protege reglas de negocio
- el validator protege la forma minima del documento

## Indices y llaves unicas

Cada coleccion nueva debe analizarse desde el inicio pensando en indices.

No se deben agregar indices solo cuando la consulta ya esta lenta en produccion.

Debemos evaluar:

- indices para filtros frecuentes
- indices para ordenamientos frecuentes
- indices compuestos para combinaciones comunes de filtros
- llaves unicas cuando un valor no debe repetirse

Preguntas practicas:

- Que campos aparecen en `$match` con mayor frecuencia
- Que campos se usan para ordenar
- Que combinaciones de filtros se repiten
- Que campos deben ser unicos por regla funcional

Regla importante:

- no crear indices por intuicion solamente
- cada indice debe responder a una necesidad concreta de consulta o integridad

## Escalabilidad del modelo

El diseno debe pensar en como puede crecer la informacion con el tiempo.

Debemos revisar:

- crecimiento en numero de documentos
- crecimiento en tamano de cada documento
- crecimiento de arreglos embebidos
- frecuencia de actualizacion
- frecuencia de lectura
- consultas historicas vs consultas operativas

Se debe tener cuidado con:

- documentos demasiado grandes
- arreglos que puedan crecer sin limite
- relaciones que obliguen a demasiados cruces frecuentes
- estructuras que dificulten agregar indices utiles

## Reglas para repositorios Mongo

Los repositorios Mongo concretos viven dentro del modulo.

Referencia de estructura:

- repositorio Mongo del modulo:
  `modules/tareas/infrastructure/persistence/mongo/tarea_repository.py`
- pipeline del modulo:
  `modules/proyectos/infrastructure/persistence/mongo/pipelines/listar_proyectos_pipeline.py`
- piezas compartidas de Mongo:
  `shared/infrastructure/persistence/mongo/`

Reglas:

- el puerto del repositorio vive en `application`
- la implementacion concreta vive en `infrastructure/persistence/mongo/`
- la logica especifica del pipeline vive en el modulo
- lo reutilizable entre modulos puede vivir en `shared`

## Reglas para construccion de pipelines

Los pipelines deben construirse pensando en costo y selectividad.

### Principios generales

- poner los `$match` lo mas al inicio posible
- reducir el conjunto de documentos antes de hacer cruces
- evitar `lookup` innecesarios
- proyectar solo los campos necesarios
- paginar siempre que el caso de uso lo requiera
- revisar si un indice adicional puede beneficiar la consulta

### Orden recomendado

En general, preferimos este enfoque:

1. `$match` inicial para reducir documentos.
2. `$sort` soportado por indice cuando sea posible.
3. `$lookup` solo si realmente hace falta.
4. `$project` para recortar campos.
5. Paginacion con `facet` o estrategia equivalente.

### Sobre los `lookup`

Los `lookup` son utiles, pero no deben convertirse en la solucion por defecto.

Reglas:

- evitar hacer tantos cruces como sea posible
- si un filtro puede aplicarse antes del `lookup`, debe ir antes
- si el cruce es muy frecuente, evaluar si el modelo puede mejorar
- si un dato se consulta constantemente y cambia poco, evaluar si conviene desnormalizar

### Sobre la paginacion

Las consultas que puedan crecer deben paginarse.

Referencia compartida:

- `shared/infrastructure/persistence/mongo/pipeline_builder.py`

Referencias del proyecto:

- `modules/proyectos/infrastructure/persistence/mongo/pipelines/listar_proyectos_pipeline.py`
- `modules/tareas/infrastructure/persistence/mongo/listar_tareas_pipeline.py`

## Checklist antes de crear una coleccion nueva

- La coleccion ya fue modelada en Moon Modeler
- Se evaluo como crecera la informacion en el tiempo
- Se definieron campos obligatorios y opcionales
- Se identificaron campos unicos
- Se definieron indices iniciales
- Se penso el validator de Mongo
- Ya se sabe en que modulo vivira el schema
- La coleccion quedara registrada en `registry.py`
- Se identificaron las consultas mas frecuentes
- Se sabe si hara falta paginacion
- Se minimizaron los `lookup` necesarios

## Checklist antes de aprobar un pipeline

- Los `$match` estan al inicio
- La consulta usa los indices correctos
- El `lookup` es realmente necesario
- Se esta proyectando solo lo necesario
- La consulta pagina cuando corresponde
- El pipeline sigue siendo legible y mantenible

## Relacion con la arquitectura hexagonal

Este manual no reemplaza el manual de arquitectura.

La regla es:

- la decision de usar Mongo pertenece a infraestructura
- el modelado del agregado sigue guiado por el dominio y los casos de uso
- los puertos permanecen en `application`
- los repositorios concretos, schemas y pipelines viven en el adaptador Mongo del modulo

Referencia principal:

- [docs/arquitectura_hexagonal.md](docs/arquitectura_hexagonal.md)

## Regla final

En Mongo no disenamos solo para que funcione hoy.

Disenamos para que:

- los datos se mantengan consistentes
- las consultas escalen
- los pipelines sigan siendo legibles
- el modelo soporte el crecimiento del negocio
