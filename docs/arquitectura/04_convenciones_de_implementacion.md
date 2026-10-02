# Convenciones de implementacion

## Estructura esperada de un modulo

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
        dependencies.py
        routes.py
        schemas.py
      persistence/
        mongo/
          schema/
          pipelines/             # builders de agregacion (si aplica)
          xxx_mapper.py          # solo si el mapeo es extenso (ver seccion Mapeo)
          xxx_repository.py
    bootstrap.py
```

## Regla obligatoria de pruebas unitarias

Todo cambio nuevo de negocio o de aplicacion debe venir acompanado de pruebas unitarias en Python para la logica que se desarrollo o modifico.

Reglas:

- Si se crea o ajusta un `service`, debe agregarse o actualizarse su prueba unitaria.
- Si se agrega logica de dominio, validaciones o reglas de negocio, debe cubrirse con pruebas unitarias.
- Si se corrige un bug, la correccion debe incluir al menos una prueba que reproduzca el caso corregido.
- Si por una restriccion real no es posible agregar la prueba en el mismo cambio, debe dejarse documentado explicitamente el motivo y el riesgo pendiente.

Convencion sugerida:

- Usar `pytest`.
- Nombrar archivos como `test_<componente>.py`.
- Priorizar pruebas de `domain/` y `application/` por encima de pruebas de framework.
- Evitar que las pruebas unitarias dependan de Mongo real, FastAPI levantado o servicios externos.

## Ubicacion y estructura de pruebas

Las pruebas no deben vivir dentro de `modules/` ni mezcladas con el codigo fuente.
La ubicacion recomendada es una carpeta raiz `tests/` que refleje la estructura del codigo.

Estructura sugerida:

```text
tests/
  unit/
    shared/
      application/
      domain/
      infrastructure/
    modules/
      nombre_modulo/
        application/
          services/
        domain/
  integration/
    shared/
    modules/
  fixtures/
  conftest.py
```

Reglas:

- `tests/unit/` debe espejar `shared/` y `modules/`.
- Las pruebas unitarias de `domain/` y `application/` son la prioridad principal.
- `tests/integration/` se reserva para pruebas que involucren framework, persistencia real o integraciones.
- La estructura de pruebas debe mantenerse sincronizada con la estructura del codigo que se va migrando.

Ejemplos:

- `modules/personas/application/services/crear_persona.py`
  -> `tests/unit/modules/personas/application/services/test_crear_persona.py`
- `shared/application/service_invocation/service.py`
  -> `tests/unit/shared/application/service_invocation/test_service.py`

## Convenciones de nombres

- Servicios: verbo + objeto, por ejemplo `crear_tarea.py`, `listar_proyectos.py`
- Puertos: `<entidad>_repository.py`
- Repositorios concretos: `mongo_<entidad>_repository.py` o equivalente del modulo
- DTOs: un archivo por caso de uso o accion
- Errores de dominio: `domain/errors.py`

| Patron | Ejemplo |
| --- | --- |
| `XxxService` con `.ejecutar()` | `CrearTareaService` |
| `XxxRepositoryPort` | `TareaRepositoryPort` |
| `MongoXxxRepository` | `MongoTareaRepository` |
| `XxxPipelineBuilder` | `TareaPipelineBuilder` |
| `XxxDTO` | `CrearTareaDTO`, `TareaDTO` |
| `xxx_mapper.py` (opcional) | `curso_mapper.py` |
| `_doc_a_entidad` / `_entidad_a_doc` | funciones privadas de mapeo Mongo |

## Servicios: cuando usar uno o varios metodos

Por defecto: una accion de negocio = una clase con `ejecutar()`.

```python
CrearTareaService.ejecutar()
CambiarEstadoTareaService.ejecutar()
```

Esto aplica cuando cada accion tiene dependencias, validaciones o permisos distintos.
No tiene sentido agruparlas porque cambiar una no afecta a las demas.

Usa multiples metodos cuando realmente estas modelando una capacidad compartida o un conjunto de consultas cohesionadas.

```python
class BuscadorTareasService:
    async def por_proyecto(self, proyecto_id): ...
    async def por_persona(self, persona_id): ...
    async def mis_asignadas(self, persona_id): ...
```

Pregunta guia:

- Si cambias una de esas operaciones, es probable que debas tocar las demas. Si si, probablemente van juntas.
- Si no, es mejor separarlas en clases distintas.

## Patrones canonicos de codigo

Estos ejemplos no buscan ser completos; funcionan como referencia corta del estilo esperado en este backend.

### Caso de uso / service

```python
# modules/<modulo>/application/services/crear_xxx.py
class CrearXxxService:
    def __init__(self, repositorio: XxxRepositoryPort) -> None:
        self._repositorio = repositorio

    async def ejecutar(self, dto: CrearXxxDTO) -> XxxDTO:
        entidad = Xxx.crear(...)
        await self._repositorio.guardar(entidad)
        return XxxDTO.desde_entidad(entidad)
```

### Puerto de repositorio

```python
# modules/<modulo>/application/ports/xxx_repository.py
from abc import ABC, abstractmethod

class XxxRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, xxx: Xxx) -> None: ...

    @abstractmethod
    async def obtener_por_id(self, xxx_id: str) -> Xxx | None: ...
```

### Repositorio Mongo

El repositorio recibe `db` por constructor (inyeccion explicita, no singleton global).
El mapeo entre documentos Mongo y entidades se hace con funciones privadas a nivel modulo (ver seccion **Mapeo de documentos Mongo**).

```python
# modules/<modulo>/infrastructure/persistence/mongo/xxx_repository.py
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.<modulo>.application.ports.xxx_repository import XxxRepositoryPort
from modules.<modulo>.domain.entities.xxx import XxxEntity


def _doc_a_entidad(doc: dict) -> XxxEntity:
    return XxxEntity(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        # ... resto de campos
    )


def _entidad_a_doc(xxx: XxxEntity) -> dict:
    return {
        "nombre": xxx.nombre,
        # ... resto de campos
    }


class MongoXxxRepository(XxxRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["xxx"]

    async def guardar(self, xxx: XxxEntity) -> str:
        doc = _entidad_a_doc(xxx)
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def obtener_por_id(self, xxx_id: str) -> XxxEntity | None:
        if not ObjectId.is_valid(xxx_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(xxx_id)})
        return _doc_a_entidad(doc) if doc else None
```

### Pipeline Mongo

Para consultas complejas o agregaciones, usar builders de pipeline como clases en vez de armar listas largas inline dentro del repositorio.

Ubicacion esperada:

```text
modules/
  <modulo>/
    infrastructure/
      persistence/
        mongo/
          pipelines/
            listar_xxx_pipeline.py
```

Reglas:

- Heredar de `shared/infrastructure/persistence/mongo/pipeline_builder.py`.
- Nombrar la clase como `XxxPipelineBuilder`.
- Cada metodo del builder debe representar una intencion de negocio o de consulta, no solo un operador suelto de Mongo.
- El repositorio es quien orquesta el builder y llama `construir()`.
- Si la consulta es trivial, puede quedarse inline en el repositorio. Si empieza a crecer en filtros, `lookup`, `project`, ordenamientos o paginacion, debe moverse a un builder.

Ejemplo de estilo esperado:

```python
class ListarXxxPipelineBuilder(
    ConstructorPipelineBase["ListarXxxPipelineBuilder"]
):
    def filtrar_activos(self) -> "ListarXxxPipelineBuilder":
        return self.agregar({"$match": {"activo": True}})

    def ordenar_por_fecha(self) -> "ListarXxxPipelineBuilder":
        return self.agregar({"$sort": {"fecha": -1, "_id": -1}})
```

En el repositorio:

```python
builder = (
    ListarXxxPipelineBuilder()
    .filtrar_activos()
    .ordenar_por_fecha()
    .paginar(pagina=pagina, limite=limite)
)
pipeline = builder.construir()
```

### Mapeo de documentos Mongo

El mapeo entre documentos Mongo (dicts) y entidades de dominio se hace con funciones privadas
(prefijo `_`) a nivel modulo dentro del mismo archivo del repositorio.

Funciones canonicas:

- `_doc_a_entidad(doc: dict) -> XxxEntity` — convierte un documento Mongo a entidad de dominio
- `_entidad_a_doc(xxx: XxxEntity) -> dict` — convierte una entidad a documento para guardar
- `_doc_a_resumen(doc: dict) -> XxxResumenDTO` — convierte proyecciones de pipeline a DTOs de lectura

Estas funciones son privadas al modulo; solo el repositorio del mismo archivo las usa.

**Cuando extraer a `xxx_mapper.py`:**

Mover el mapeo a un archivo separado `infrastructure/persistence/mongo/xxx_mapper.py` cuando
el archivo del repositorio supera aproximadamente 200 lineas o cuando hay tres o mas tipos de
documentos distintos que convertir (por ejemplo, entidad principal, subdocumentos complejos y
multiples DTOs de proyeccion).

No extraer por adelantado. Si el repositorio es legible y manejable, las funciones van inline.

Estructura cuando se extrae:

```text
persistence/
  mongo/
    xxx_mapper.py       # _doc_a_entidad, _entidad_a_doc, _doc_a_resumen
    xxx_repository.py   # importa desde xxx_mapper
```

### Ruta HTTP

```python
# modules/<modulo>/infrastructure/api/routes.py
router = APIRouter(prefix="/api/xxx", tags=["xxx"])

@router.post(
    "",
    status_code=201,
    summary="Crea un nuevo xxx",
    response_description="ID del recurso creado",
    responses={
        409: {"description": "Conflicto de negocio (p. ej. duplicado)"},
        422: {"description": "Datos de entrada invalidos"},
    },
)
async def crear_xxx(
    body: CrearXxxRequest,
    service: Annotated[CrearXxxService, Depends(get_crear_xxx_service)],
) -> XxxResponse:
    ...
```

### Inyeccion de dependencias

```python
# modules/<modulo>/infrastructure/api/dependencies.py
def get_crear_xxx_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> CrearXxxService:
    return CrearXxxService(MongoXxxRepository(db))
```

## Forma esperada de trabajo

1. Modelar o ajustar entidades y errores en `domain/`
2. Definir DTOs, puertos y servicios en `application/`
3. Implementar adaptadores HTTP y persistencia en `infrastructure/`
4. Agregar o actualizar pruebas unitarias para la logica nueva o modificada
5. Conectar dependencias en `dependencies.py`
6. Registrar el modulo en `bootstrap.py`
7. Si aplica, registrar el modulo en `shared/bootstrap/application.py`

## Documentacion de rutas y servicios

### Rutas (FastAPI)

Documentar via parametros del decorador, no con docstrings en la funcion:

- `summary`: obligatorio, una linea, verbo en tercera persona ("Crea", "Obtiene", "Elimina").
- `responses`: documentar solo los errores de negocio 4xx relevantes. No documentar 500.
- `response_description`: opcional, solo si el cuerpo de respuesta exitosa necesita aclaracion.
- No usar `description=` en el decorador salvo que el comportamiento no sea obvio por el `summary`.

### Servicios (application layer)

Docstring en `ejecutar()` unicamente cuando el contrato no es obvio por los parametros:

```python
async def ejecutar(self, id_xxx: str, dto: CambiarEstadoXxxDTO, ...) -> None:
    """Valida la transicion de estado y registra el cambio en el historial.

    Raises:
        XxxNoEncontrado: si el id no corresponde a ningun registro.
        TransicionEstadoInvalida: si el estado destino no es alcanzable desde el actual.
    """
```

Reglas:
- Primera linea: que hace, en una oracion.
- Seccion `Raises:` solo si el servicio lanza `DomainError` propios - listar cuales y cuando.
- No documentar parametros obvios por su nombre y tipo.
- No docstring si el metodo es trivial (p. ej., solo delega al repositorio).

## Reglas practicas

- Las rutas no deben cargar logica de negocio compleja.
- Los servicios deben depender de puertos, no de implementaciones concretas.
- Los schemas HTTP viven en `infrastructure/api/schemas.py`.
- Los documentos o mapeos de Mongo viven en `infrastructure/persistence/mongo/`.
- Los pipelines complejos de Mongo deben vivir en `infrastructure/persistence/mongo/pipelines/` como builders dedicados.
- Las pruebas unitarias deben validar la logica propia del modulo, no el comportamiento interno de FastAPI o Motor.
- Antes de duplicar un helper o una abstraccion, revisar `shared/`.
- Evita interfaces gigantes con muchos metodos.
- No uses `shared/` como cajon de sastre.
- No crear `__init__.py` en los directorios del modulo - el proyecto usa Python 3.3+ namespace packages y ningun modulo existente los usa.

## Convenciones operativas del proyecto

- Los cambios de schema de Mongo se versionan y sincronizan con `scripts.mongo.sync_schema`.

## Referencias utiles

- [../arquitectura_hexagonal.md](../arquitectura_hexagonal.md) para decisiones de capas, `shared/` y reglas de dependencia
- [../mongo/modelado_y_consultas.md](../mongo/modelado_y_consultas.md) si vas a construir consultas, agregaciones o `PipelineBuilder`
- [../mongo/gestion_de_schemas.md](../mongo/gestion_de_schemas.md) si vas a tocar validadores, indices o sincronizacion de schemas
