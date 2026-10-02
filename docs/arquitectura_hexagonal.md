# Manual de Arquitectura Hexagonal

## Objetivo de este documento

Este manual explica como organizamos el proyecto usando arquitectura hexagonal, que patrones de diseño utilizamos, como se relaciona todo con SOLID y en que casos se debe agregar algo nuevo a `shared`.

La idea es que cualquier persona del equipo pueda:

- entender la intencion de la arquitectura
- crear modulos nuevos sin mezclar responsabilidades
- saber donde ubicar cada clase o archivo
- reutilizar correctamente las piezas comunes

## Que es la arquitectura hexagonal

La arquitectura hexagonal, tambien conocida como `Ports and Adapters`, busca separar el nucleo de negocio de los detalles tecnicos.

En la practica significa esto:

- el negocio no debe depender de FastAPI, Mongo, GCP ni SDKs de proveedores
- la aplicacion define contratos y casos de uso
- la infraestructura implementa esos contratos
- el punto de composicion conecta las implementaciones reales

La dependencia siempre debe apuntar hacia adentro:

```text
infrastructure -> application -> domain
bootstrap -> infrastructure + application
```

El dominio no debe conocer frameworks ni SDKs.

## Como esta aplicada en ms-continuum

### Capa `domain`

Responsabilidad:

- reglas de negocio
- entidades
- errores de dominio

Archivos base:

- `shared/domain/entities/base.py`
- `shared/domain/errors.py`

Reglas:

- no importa FastAPI
- no importa repositorios concretos
- no importa SDKs de proveedores
- debe poder probarse sin infraestructura

Ejemplo:

- `modules/tareas/domain/entities/tarea.py`
- `modules/proyectos/domain/errors.py`

### Capa `application`

Responsabilidad:

- casos de uso
- puertos
- DTOs de entrada y salida de aplicacion
- errores de aplicacion

Archivos base:

- `shared/application/errors.py`
- `shared/application/persistence/unit_of_work.py`
- `shared/application/service_invocation/`
- `shared/application/dto/pagination.py`

Reglas:

- depende de `domain`
- no debe importar implementaciones concretas de `infrastructure`
- modela capacidades del sistema, no proveedores

Ejemplo:

- `modules/tareas/application/ports/tarea_repository.py`
- `modules/proyectos/application/services/`

### Capa `infrastructure`

Responsabilidad:

- adaptadores concretos
- rutas HTTP
- repositorios reales
- integraciones externas
- persistencia

Archivos base:

- `shared/infrastructure/api/error_handlers.py`
- `shared/infrastructure/persistence/mongo/`
- `shared/infrastructure/gcp/`

Reglas:

- implementa puertos definidos en `application`
- puede usar frameworks, SDKs y detalles tecnicos
- no debe meter reglas de negocio que pertenezcan al dominio

Ejemplo:

- `modules/tareas/infrastructure/api/routes.py`
- `modules/tareas/infrastructure/persistence/mongo/tarea_repository.py`

### Capa `bootstrap`

Responsabilidad:

- composicion
- registro de modulos
- conexion de dependencias concretas

Archivos base:

- `shared/bootstrap/application.py`
- `shared/bootstrap/dependencies.py`
- `modules/<modulo>/bootstrap.py`

Reglas:

- aqui si se permite conocer implementaciones concretas
- no contiene reglas de negocio
- conecta puertos con adaptadores

Ejemplo:

- `shared/bootstrap/application.py` crea el `FastAPI app` y registra modulos
- `modules/proyectos/bootstrap.py` expone el registro del modulo
- `shared/bootstrap/dependencies.py` construye dependencias compartidas

## Patrones de diseño que usamos

### 1. Ports and Adapters

Es el patron principal de la arquitectura.

Ejemplo:

- puerto: `modules/tareas/application/ports/tarea_repository.py`
- adaptador: `modules/tareas/infrastructure/persistence/mongo/tarea_repository.py`

La aplicacion conoce el puerto.
La infraestructura implementa el puerto.

### 2. Use Case / Application Service

Cada accion de negocio puntual se modela como una clase de caso de uso con un unico metodo `ejecutar()`.

Ejemplos:

- `modules/tareas/application/services/crear_tarea.py`
- `modules/tareas/application/services/obtener_tarea.py`
- `modules/tareas/application/services/listar_tareas.py`
- `modules/tareas/application/services/cambiar_estado_tarea.py`

Regla:

- si la clase representa una accion puntual, usamos `XxxService.ejecutar()`
- si representa una capacidad compartida, puede tener varios metodos

Ejemplo de capacidad compartida:

- `shared/application/service_invocation/service.py`

### 3. Repository

El repositorio encapsula acceso a datos del agregado o entidad.

Patron que seguimos:

- puerto en `application`
- implementacion concreta en `infrastructure`

Ejemplo:

- `TareaRepositoryPort`
- `MongoTareaRepository`

### 4. Dependency Injection

Las dependencias no se crean dentro del caso de uso.
Se inyectan desde dependencias HTTP o desde `bootstrap`.

Ejemplos:

- `modules/tareas/infrastructure/api/dependencies.py`
- `shared/bootstrap/dependencies.py`

### 5. Factory / Composition Root

El proyecto usa un punto de composicion global para construir el `app` y
puntos de composicion por modulo para exponer su registro.

Ejemplo:

- `shared/bootstrap/application.py`
- `modules/tareas/bootstrap.py`

Esto evita que dominio o aplicacion conozcan FastAPI directamente.

### 6. Builder

Para Mongo usamos un constructor base de pipelines reutilizable.

Archivos:

- base compartida: `shared/infrastructure/persistence/mongo/pipeline_builder.py`
- pipeline concreto de un modulo: `modules/proyectos/infrastructure/persistence/mongo/pipelines/listar_proyectos_pipeline.py`

Regla:

- lo reutilizable vive en `shared`
- la logica especifica del pipeline vive en el modulo

### 7. Unit of Work

El proyecto ya cuenta con un puerto de `UnitOfWork` para operaciones que
necesiten coordinar transacciones o sesiones.

Archivos:

- puerto: `shared/application/persistence/unit_of_work.py`
- implementacion Mongo: `shared/infrastructure/persistence/mongo/unit_of_work.py`

Esto ayuda a que la aplicacion no dependa de sesiones concretas de base de
datos. No todos los casos de uso actuales lo emplean todavia.

## Como se relaciona esto con SOLID

### S: Single Responsibility Principle

Cada clase debe tener una sola razon para cambiar.

Ejemplos:

- `CrearTareaService` solo crea tareas
- `MongoTareaRepository` solo resuelve persistencia
- `TareaPipelineBuilder` solo construye pipelines

Que evitar:

- servicios que hacen validacion, persistencia, mapping y HTTP al mismo tiempo
- rutas que implementan reglas de negocio complejas

### O: Open/Closed Principle

El sistema debe poder extenderse sin modificar demasiado el nucleo.

Ejemplos:

- agregar otro repositorio concreto sin cambiar el puerto
- agregar otro cliente de invocacion externa sin cambiar la capacidad de `application`

### L: Liskov Substitution Principle

Una implementacion concreta debe poder sustituir al puerto sin romper el comportamiento esperado.

Ejemplo:

- `MongoTareaRepository` y otro repositorio real deben respetar el contrato de `TareaRepositoryPort`

### I: Interface Segregation Principle

Los contratos deben ser pequenos y enfocados.

Ejemplo:

- `TareaRepositoryPort` expone solo lo que el modulo necesita
- no creamos interfaces gigantes con decenas de metodos irrelevantes

### D: Dependency Inversion Principle

La aplicacion depende de abstracciones, no de implementaciones concretas.

Ejemplo:

- `CrearTareaService` depende de `TareaRepositoryPort`
- `shared/application/service_invocation/service.py` depende de puertos
- `shared/bootstrap/dependencies.py` conecta la implementacion concreta

Este principio es el que mas directamente sostiene la arquitectura hexagonal.

## Convenciones del proyecto

### Nombres

- `XxxPort`: contrato de aplicacion
- `XxxRepositoryPort`: contrato de persistencia
- `XxxService` con `ejecutar()`: caso de uso
- `MongoXxxRepository`, `ClienteCloudRun`: implementaciones concretas
- `XxxPipelineBuilder`: constructor de pipeline Mongo

### Documentacion

Regla general:

- rutas HTTP: `OpenAPI-first`
- servicios y componentes: docstrings estilo Google

Referencia:

- `modules/tareas/infrastructure/api/routes.py`
- `modules/proyectos/application/services/`

### Orden de rutas

Convencion recomendada en archivos `routes.py`:

- `# Rutas de coleccion`
- `# Rutas de recurso`
- `# Acciones de negocio`

### Inyeccion de dependencias en FastAPI

Usamos `Annotated` en las rutas para que el tipo real quede claro.

Ejemplo:

```python
service: Annotated[CrearTareaService, Depends(get_crear_tarea_service)]
```

## Cuando algo debe ir en `shared`

Esta es una de las decisiones mas importantes del proyecto.

`shared` no es un cajon de sastre.
Solo debe contener piezas que realmente puedan ser reutilizadas por varios modulos o por toda la aplicacion.

### Debe ir en `shared` cuando

- es una regla transversal a varios modulos
- es una abstraccion reusable de aplicacion
- es infraestructura compartida por varios modulos
- es una utilidad tecnica comun
- no pertenece funcionalmente a un modulo de negocio especifico

Ejemplos correctos en `shared`:

- `shared/domain/errors.py`
- `shared/application/errors.py`
- `shared/application/dto/pagination.py`
- `shared/application/persistence/unit_of_work.py`
- `shared/application/service_invocation/`
- `shared/infrastructure/api/error_handlers.py`
- `shared/infrastructure/persistence/mongo/pipeline_builder.py`
- `shared/infrastructure/gcp/secret_manager.py`

### No debe ir en `shared` cuando

- pertenece a una feature concreta
- solo lo usa un modulo
- contiene reglas de negocio especificas de un contexto
- es un pipeline, mapper, schema o repositorio concreto de un unico modulo

Ejemplos que deben quedarse en el modulo:

- `modules/tareas/domain/entities/tarea.py`
- `modules/proyectos/application/services/crear_proyecto.py`
- `modules/tareas/infrastructure/persistence/mongo/pipelines/listar_tareas_pipeline.py`

### Regla practica para decidir

Antes de mover algo a `shared`, se deben hacer estas preguntas:

1. ¿Lo usan o lo usaran varios modulos de verdad?
2. ¿Es una capacidad transversal y no una regla del negocio de un modulo?
3. ¿Moverlo a `shared` mejora claridad o solo reduce duplicacion aparente?

Si la respuesta no es claramente `si`, debe dejarse en el modulo.

## Como crear un modulo nuevo

Base recomendada:

```text
modules/
  nombre_modulo/
    application/
      dto/
      ports/
      services/
    domain/
      entities/
      errors.py
    infrastructure/
      api/
      persistence/
        mongo/
          schema/
    bootstrap.py
```

Pasos:

1. definir entidades y errores en `domain`
2. definir DTOs y puertos en `application`
3. crear un servicio por caso de uso
4. implementar adaptadores en `infrastructure`
5. exponer rutas HTTP en `infrastructure/api`
6. exponer `register_module()` en su `bootstrap.py`
7. registrar ese modulo en `shared/bootstrap/application.py`

Referencias practicas:

- `modules/tareas/`
- `modules/proyectos/`

## Que hacer si un modulo crece mucho

Cuando un modulo empieza a tener varios contextos internos, se puede dividir en submodulos.

Ejemplo:

```text
modules/
  usuarios/
    bootstrap.py
    shared/
      domain/
      application/
    submodules/
      perfiles/
        application/
        domain/
        infrastructure/
        bootstrap.py
      roles/
        application/
        domain/
        infrastructure/
        bootstrap.py
```

Reglas:

- cada submodulo puede tener su propio `domain`, `application`, `infrastructure`
- el modulo padre registra los submodulos
- lo comun del modulo padre puede vivir en `modules/<modulo>/shared/`
- lo realmente global sigue en `shared/`

## Errores comunes que se deben evitar

- meter logica de negocio en rutas FastAPI
- hacer que `application` importe `Mongo`, `FastAPI`, `requests` o SDKs cloud
- mover demasiado pronto cosas a `shared`
- crear repositorios o interfaces gigantes
- mezclar proveedor e intencion en `application`
- usar `shared` como carpeta de cosas "varias"

## Checklist rapido para revisar una nueva feature

- ¿El dominio esta libre de frameworks y proveedores?
- ¿La aplicacion depende de puertos y no de implementaciones concretas?
- ¿La infraestructura implementa contratos en lugar de definir negocio?
- ¿El modulo se registra desde `bootstrap`?
- ¿Solo se movio a `shared` lo que es realmente comun?
- ¿Las rutas y servicios quedaron documentados con el estandar del proyecto?

## Referencias dentro del proyecto

- composicion del app: `shared/bootstrap/application.py`
- bootstrap por modulo: `modules/<modulo>/bootstrap.py`
- wiring de dependencias compartidas: `shared/bootstrap/dependencies.py`
- errores base: `shared/domain/errors.py`
- errores de aplicacion: `shared/application/errors.py`
- invocacion de servicios externos: `shared/application/service_invocation/`
- integraciones GCP: `shared/infrastructure/gcp/`
- persistencia Mongo compartida: `shared/infrastructure/persistence/mongo/`
- modulos funcionales actuales: `modules/organizaciones/`, `modules/personas/`, `modules/proyectos/`, `modules/tareas/`

## Conclusión

La arquitectura hexagonal no se trata de tener mas carpetas.
Se trata de proteger el negocio de los detalles tecnicos, mantener el codigo facil de probar y permitir que el sistema crezca sin que cada cambio rompa todo lo demas.

Si existe alguna duda sobre donde ubicar una pieza, esta regla final puede servir de apoyo:

- si es negocio, va hacia adentro
- si es tecnologia, va hacia afuera
- si es transversal de verdad, puede ir a `shared`
- si es de una feature concreta, se queda en su modulo
