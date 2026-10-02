# Modulo de Ejemplo: Tareas

Este modulo existe para mostrar como crear una feature completa siguiendo arquitectura hexagonal.

## Estructura

```text
modules/ejemplo_tareas/
  application/
    dto/           # contratos de entrada para casos de uso
    ports/         # interfaces que necesita la aplicacion
    services/      # casos de uso
  domain/
    entities/      # entidades del dominio
    errors.py      # errores de negocio
  infrastructure/
    api/           # routes, schemas y dependencias HTTP
    persistence/   # adaptadores concretos de repositorio
  bootstrap.py     # registro del modulo en FastAPI
```

## Flujo recomendado para crear un modulo nuevo

1. Define las entidades y errores del dominio.
2. Crea los DTOs de entrada de aplicacion.
3. Declara los puertos que la aplicacion necesita.
4. Implementa un servicio por caso de uso.
5. Crea los adaptadores de infraestructura.
6. Expone el modulo por HTTP con `routes.py`.
7. Registra el router desde el `bootstrap.py` del modulo.

## Buenas practicas que muestra este ejemplo

- El dominio no importa FastAPI ni bases de datos.
- La aplicacion depende de puertos, no de implementaciones.
- La API convierte request/response HTTP sin contaminar el dominio.
- El repositorio concreto puede cambiarse sin tocar los servicios.
- El modulo se conecta al `app` desde composicion, no desde el dominio.
- Los pipelines de Mongo viven en el modulo, no en `shared`.

## Convencion para servicios del modulo

- `CrearTareaService`, `ObtenerTareaService`, `ListarTareasService` y `CompletarTareaService` son casos de uso.
- Cada caso de uso tiene un solo metodo publico: `ejecutar()`.
- Esta convencion aplica cuando la clase representa una accion de negocio puntual.
- Si una clase ofreciera una capacidad compartida, podria tener varios metodos publicos y seguir viviendo en `application`, pero ya no seria un caso de uso tan estricto.

## Convencion para puertos y adaptadores

- `TareaRepositoryPort` define el contrato que necesita la aplicacion.
- `MongoTareaRepository` es el adaptador concreto de infraestructura.
- El archivo del puerto se nombra por responsabilidad: `application/ports/tarea_repository.py`.
- El archivo del adaptador se nombra segun la tecnologia y se ubica bajo su carpeta tecnica:
  `infrastructure/persistence/mongo/tarea_repository.py`.

## Endpoints del ejemplo

- `POST /api/ejemplo/tareas`
- `GET /api/ejemplo/tareas`
- `GET /api/ejemplo/tareas/{tarea_id}`
- `PATCH /api/ejemplo/tareas/{tarea_id}/completar`

## Donde mirar cada pieza

- Entidad de dominio: `domain/entities/tarea.py`
- Errores de negocio: `domain/errors.py`
- Puerto del repositorio: `application/ports/tarea_repository.py`
- Casos de uso: `application/services/`
- Dependencias HTTP: `infrastructure/api/dependencies.py`
- Schemas HTTP: `infrastructure/api/schemas.py`
- Rutas: `infrastructure/api/routes.py`
- Adaptador concreto: `infrastructure/persistence/mongo/tarea_repository.py`
- Pipeline Mongo del modulo: `infrastructure/persistence/mongo/pipelines/tarea_pipeline.py`
- Registro del modulo: `bootstrap.py`

## Sustitucion para produccion

El repositorio actual conserva datos en memoria para que el ejemplo funcione sin depender de Mongo o MariaDB.
Se nombra `MongoTareaRepository` a proposito para enseñar la convencion recomendada en infraestructura: tecnologia + agregado.

## Regla para pipelines Mongo

- La base reutilizable del constructor vive en `shared/infrastructure/persistence/mongo/pipeline_builder.py`.
- Los pipelines concretos de cada feature viven en el modulo, por ejemplo:
  `modules/ejemplo_tareas/infrastructure/persistence/mongo/pipelines/tarea_pipeline.py`
- El repositorio Mongo del modulo es quien usa ese pipeline builder.

## Estandar de documentacion aplicado al modulo

Para este modulo tomamos estas decisiones:

- Las rutas usan `summary`, `description`, `response_description` y `responses`.
- Las funciones de rutas tienen docstrings cortos orientados al caso de uso.
- Los servicios usan docstrings estilo Google en clase y en `ejecutar()`.
- La documentacion HTTP explica comportamiento de negocio y errores esperables.

Archivos donde ver el ejemplo:

- Rutas documentadas: `infrastructure/api/routes.py`
- Servicios documentados: `application/services/`

## Si este modulo creciera en submodulos

Si `ejemplo_tareas` creciera mucho, podria dividirse asi:

```text
modules/
  ejemplo_tareas/
    bootstrap.py
    shared/
      application/
      domain/
    submodules/
      catalogo/
        application/
        domain/
        infrastructure/
        bootstrap.py
      seguimiento/
        application/
        domain/
        infrastructure/
        bootstrap.py
```

En ese escenario:

- `catalogo` y `seguimiento` tendrian sus propios casos de uso, puertos, rutas y repositorios.
- `modules/ejemplo_tareas/bootstrap.py` registraria ambos submodulos.
- Lo comun a ambos viviria en `modules/ejemplo_tareas/shared/`.
- Lo reutilizable a nivel de toda la plantilla seguiria viviendo en `shared/`.
