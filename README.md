# Template FastAPI Backend

Plantilla base para proyectos con arquitectura hexagonal sobre FastAPI.

## Estructura

```text
shared/
  application/     # capacidades del sistema: DTOs, puertos y servicios
  bootstrap/       # composicion de dependencias y creacion del app
  domain/          # entidades y errores puros del negocio
  infrastructure/  # adaptadores HTTP, persistencia y proveedores externos
  utils/           # utilidades compartidas y agnosticas
config/            # configuracion y logging
main.py            # punto de entrada
```

## Regla de dependencias

- `domain` no depende de FastAPI, bases de datos ni SDKs.
- `application` depende de `domain`, pero no de `infrastructure`.
- `infrastructure` implementa los puertos definidos en `application`.
- `application` se nombra por capacidad, no por proveedor.
- `infrastructure` se agrupa por proveedor cuando integra servicios externos.
- `bootstrap` conecta implementaciones concretas con los servicios.

## Convenciones de nombres

- `XxxPort`: contrato que define una capacidad o dependencia de aplicacion.
- `XxxRepositoryPort`: puerto para persistencia de un agregado o entidad.
- `XxxService` con metodo `ejecutar()`: un caso de uso puntual de negocio.
- `XxxService` con varios metodos: una capacidad reusable, no un caso de uso unico.
- `MongoXxxRepository`, `MariaDbXxxRepository`, `AwsXxxClient`: adaptadores concretos de infraestructura.
- `XxxPipelineBuilder`: constructor de pipelines Mongo especifico de un modulo.

## Regla para servicios de aplicacion

- Si una clase representa una accion de negocio concreta, se modela como un caso de uso con un unico metodo `ejecutar()`.
- Si una clase representa una capacidad compartida del sistema, puede tener varios metodos publicos.
- En `application/services` preferimos una clase por caso de uso para mantener responsabilidades pequenas y pruebas simples.

## Regla para adaptadores

- Los repositorios y clientes de infraestructura pueden tener varios metodos porque representan una capacidad tecnica.
- El puerto vive en `application` y la implementacion concreta vive en `infrastructure`.
- El nombre de la clase concreta debe revelar la tecnologia o proveedor.

## Modulos con submodulos

Cuando un modulo crece demasiado o empieza a tener varias capacidades de negocio relacionadas pero separables, se puede dividir en submodulos.

La regla recomendada es:

- `modules/<modulo_padre>/` agrupa el contexto funcional grande.
- `modules/<modulo_padre>/submodules/<submodulo>/` contiene una feature con autonomia propia.
- Cada submodulo puede tener su propio `domain`, `application`, `infrastructure` y `bootstrap.py`.
- El modulo padre se encarga de registrar los submodulos en su propio `bootstrap.py`.
- Solo se comparte codigo en el modulo padre cuando realmente es comun a todos sus submodulos.

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

Reglas practicas:

- Si una pieza pertenece solo a un submodulo, vive dentro de ese submodulo.
- Si una pieza es comun a varios submodulos del mismo modulo padre, puede vivir en `modules/<modulo_padre>/shared/`.
- Si una pieza es reutilizable por toda la aplicacion, entonces va en `shared/`.
- Evita que un submodulo importe directamente implementaciones concretas de otro submodulo.
- Si dos submodulos necesitan colaborar, que lo hagan mediante puertos, servicios de aplicacion o coordinacion desde el modulo padre.

## Estandar de documentacion

Usamos dos convenciones complementarias:

- `OpenAPI-first` para rutas HTTP, pensando en `docs` y `ReDoc`.
- `Google-style docstrings` para servicios, adaptadores y piezas de codigo reutilizable.

### Documentacion de rutas

Cada endpoint debe definir como minimo:

- `summary`: una frase corta en infinitivo.
- `description`: contexto funcional, reglas y comportamiento esperado.
- `response_model`: contrato de salida.
- `response_description`: descripcion corta de la respuesta exitosa.
- `responses`: errores relevantes documentados por codigo HTTP.

Formato recomendado:

```python
@router.get(
    "/{recurso_id}",
    response_model=RecursoResponse,
    summary="Obtener un recurso",
    description=(
        "Consulta el detalle de un recurso a partir de su identificador. "
        "Debe explicar el objetivo del endpoint y cualquier regla importante."
    ),
    response_description="Detalle del recurso solicitado.",
    responses={
        404: {"description": "No existe un recurso con el identificador enviado."},
    },
)
async def obtener_recurso(...):
    """Ejecuta el caso de uso de consulta del recurso."""
```

### Documentacion de servicios

Los casos de uso deben documentarse con docstrings cortos y consistentes:

- docstring de clase: responsabilidad del caso de uso
- docstring de `ejecutar()`: `Args`, `Returns` y `Raises` cuando aplique

Formato recomendado:

```python
class ObtenerRecursoService:
    """Caso de uso encargado de consultar un recurso por identificador."""

    async def ejecutar(self, recurso_id: str) -> Recurso:
        """Obtiene un recurso existente.

        Args:
            recurso_id: Identificador unico del recurso.

        Returns:
            El recurso encontrado.

        Raises:
            RecursoNoEncontradoError: Si el identificador no existe.
        """
```

### Reglas practicas

- Documenta el por que y el comportamiento, no lo obvio de la sintaxis.
- En rutas, usa descripciones orientadas a negocio, no a implementacion interna.
- En servicios, describe la responsabilidad y las reglas relevantes.
- Si una clase o funcion es trivial y el nombre ya es suficientemente claro, evita comentarios redundantes.

## Documentacion

| Documento | Contenido |
|---|---|
| [docs/ai/README.md](docs/ai/README.md) | Vision general y orden de lectura recomendado para IA |
| [docs/ai/01_sistema_y_alcance.md](docs/ai/01_sistema_y_alcance.md) | Que es la plantilla, stack y mapa de carpetas |
| [docs/ai/02_arquitectura_y_reglas.md](docs/ai/02_arquitectura_y_reglas.md) | Reglas de capas y dependencias |
| [docs/ai/03_modulos_y_flujos.md](docs/ai/03_modulos_y_flujos.md) | Modulos existentes y flujos tipicos |
| [docs/ai/04_convenciones_de_implementacion.md](docs/ai/04_convenciones_de_implementacion.md) | Patrones de codigo y nombres |
| [docs/ai/05_operacion_y_entorno.md](docs/ai/05_operacion_y_entorno.md) | Variables de entorno y operacion local |
| [docs/ai/06_playbook_nuevo_modulo.md](docs/ai/06_playbook_nuevo_modulo.md) | Paso a paso para crear un modulo nuevo |
| [docs/arquitectura_hexagonal.md](docs/arquitectura_hexagonal.md) | Explicacion completa de la arquitectura y sus decisiones |
| [docs/mongo/modelado_y_consultas.md](docs/mongo/modelado_y_consultas.md) | Reglas de modelado, consultas y pipelines en MongoDB |
| [docs/mongo/gestion_de_schemas.md](docs/mongo/gestion_de_schemas.md) | Versionado, validadores e indices de MongoDB |

## Notas de la plantilla

- Los errores internos se traducen a HTTP solo en `shared/infrastructure/api/error_handlers.py`.
- La capacidad de invocacion de servicios se define en `shared/application/service_invocation/`.
- La conexion a MongoDB vive en adaptadores de infraestructura bajo `shared/infrastructure/`.
- El modulo guia para crear nuevas features esta en `modules/ejemplo_tareas/`.
- El playbook completo para un modulo nuevo esta en `docs/ai/06_playbook_nuevo_modulo.md`.
