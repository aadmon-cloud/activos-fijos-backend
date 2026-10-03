# Plantilla base para microservicios FastAPI en Cloud Run — Diseño

## Contexto

Existen varios microservicios ya desplegados en Cloud Run (`ms-continuum`, `ms-rhampholeo`, `Bifrost`) construidos con distintos grados de adherencia a la arquitectura hexagonal documentada en `UltimateBackend/.claude`. `ms-continuum` y `ms-rhampholeo` ya nacieron con la estructura hexagonal correcta (`modules/{domain,application,infrastructure}` + `shared/`), pero no llevan copiada la documentación de convenciones (`.claude/*.md`) que vive centralizada en `UltimateBackend`. `Bifrost` es legacy plano (`routers/services/db`), sin esa arquitectura.

Ningún proyecto existente tiene carpeta `tests/` (pese a que `TESTING.md` la exige) ni pipeline de CI/CD versionado — el despliegue ocurre vía la función "Continuous Deployment" nativa de Cloud Run, que crea un trigger de Cloud Build no versionado en el repo y sin caché de capas Docker, lo que fuerza una reinstalación completa de dependencias pip en cada despliegue aunque solo cambie código de aplicación.

Este repo (`fastapi-cloud-run`) será la plantilla base: un proyecto real, funcional y clonable que centraliza la arquitectura, las convenciones para Claude Code, y cierra las brechas de testing y CI/CD detectadas, para arrancar cada nuevo microservicio Cloud Run correctamente desde el día uno.

## Objetivo

Producir un repositorio plantilla que se usa **clonando y renombrando a mano** (sin cookiecutter/copier ni herramientas de scaffolding adicionales) para iniciar un nuevo microservicio Cloud Run con:

1. Arquitectura hexagonal correcta desde el inicio, con un módulo de ejemplo funcional de punta a punta (no solo carpetas vacías).
2. Documentación `.claude/*.md` adaptada de `UltimateBackend`, generalizada para cualquier microservicio nuevo.
3. Infraestructura compartida (Mongo, Secret Manager, autenticación Cloud Run↔Cloud Run) lista para usar, no solo documentada.
4. `tests/` con ejemplos reales y `cloudbuild.yaml` versionado que resuelve el problema de caché de capas Docker detectado.
5. Entorno de desarrollo local reproducible (Mongo vía docker-compose).

## Fuera de alcance

- No se introduce ningún gestor de dependencias nuevo (se mantiene `pip` + `requirements.txt`, consistente con todos los proyectos existentes).
- No se introduce GitHub Actions; se formaliza el mecanismo de Cloud Build que ya está en uso vía la Continuous Deployment nativa de Cloud Run.
- No se migra ni se toca ningún proyecto existente (`ms-continuum`, `ms-rhampholeo`, `Bifrost`, `UltimateBackend`) — esta plantilla es un repo nuevo e independiente. Migrar proyectos existentes a partir de esta plantilla queda fuera de este spec.
- No se incluye scaffolding automatizado (cookiecutter/copier); el mecanismo de uso es clonar y editar a mano.
- No se define aquí el detalle de dominio de negocio del módulo de ejemplo más allá de un CRUD mínimo de "tareas" — es un vertical slice ilustrativo, no un módulo de producción.

## Estructura de carpetas

```
fastapi-cloud-run/
  main.py                          # punto de entrada mínimo: app = create_app()
  config/
    settings.py                    # pydantic-settings, lee .env
    logger.py
  modules/
    tareas/                        # módulo de ejemplo end-to-end
      domain/
        entities.py                # entidad pura Tarea, sin dependencias externas
        errors.py
      application/
        dto/
        ports/
          tarea_repository.py      # TareaRepositoryPort (interfaz abstracta)
        services/
          crear_tarea.py           # CrearTareaService con método .ejecutar()
          listar_tareas.py         # ListarTareasService con método .ejecutar()
      infrastructure/
        api/
          routes.py                # rutas FastAPI (Annotated + Depends)
          schemas.py                # modelos Pydantic HTTP (request/response)
          dependencies.py           # wiring de dependencias vía Depends
        persistence/
          mongo/
            tarea_repository.py    # implementación Mongo del port, con _doc_a_entidad/_entidad_a_doc
      bootstrap.py                 # registra rutas del módulo + wiring de servicios/repos
  shared/
    domain/
    application/
    bootstrap/
      application.py               # create_app(): instancia FastAPI, llama register_module por módulo
    infrastructure/
      mongo/
        client.py                  # cliente Motor async, credenciales desde Secret Manager
        settings.py
      gcp/
        secret_manager.py          # helper para leer secretos de GCP Secret Manager
        cloud_run/
          client.py                # cliente HTTP para llamadas salientes autenticadas
          resolver.py               # resuelve URL del servicio Cloud Run destino
          token_provider.py        # obtiene ID tokens de GCP para llamadas salientes
      authentication/
        token_verifier.py          # verifica ID tokens entrantes de otros servicios Cloud Run
    utils/
  tests/
    unit/
      modules/
        tareas/
          domain/
            test_entities.py       # test de entidad pura, sin mocks
          application/
            test_crear_tarea.py    # test de servicio con TareaRepositoryPort mockeado
  .claude/
    ARCHITECTURE.md
    CONVENTIONS.md
    STACK.md
    TEMPLATE.md
    TESTING.md
    WORKFLOW.md
    SOLID_CHECKLIST.md
    API.md
    MONGODB.md
    MONGODB_MODELING.md
    MONGODB_QUERIES.md
  CLAUDE.md                        # entry point en la raíz: reglas críticas + índice a .claude/*.md
  docs/
    arquitectura_hexagonal.md      # versión explicativa en prosa (adaptada de UltimateBackend)
  Dockerfile                       # igual al de ms-continuum (orden de capas ya correcto)
  cloudbuild.yaml                  # build con --cache-from + tests + deploy
  docker-compose.yml               # Mongo local para desarrollo
  requirements.txt
  requirements-dev.txt
  .env.example
  pytest.ini
  README.md
```

## Módulo de ejemplo: `tareas`

Vertical slice completo y funcional, no solo carpetas vacías: crear tarea y listar tareas, persistidas en Mongo real (vía `docker-compose` en local). Sirve como:

- Plantilla a copiar/renombrar para el primer módulo real de cada proyecto nuevo.
- Referencia viva de las convenciones de `CONVENTIONS.md` (mapeo clase↔archivo, un servicio = una acción con `.ejecutar()`, funciones `_doc_a_entidad`/`_entidad_a_doc`).

## `shared/infrastructure` precargado

Se porta y generaliza desde `ms-continuum` (quitando cualquier detalle específico de ese proyecto):

- **Mongo**: cliente Motor async, con certificado/credenciales obtenidas desde Secret Manager.
- **Secret Manager**: helper simple para leer secretos de GCP.
- **Cloud Run ↔ Cloud Run**: `client.py` + `resolver.py` + `token_provider.py` para llamadas salientes autenticadas, y `authentication/token_verifier.py` para verificar tokens entrantes. Presente y funcional aunque el módulo de ejemplo no lo use — es infraestructura base para cuando el proyecto real necesite llamar a otro microservicio.

## Docker y CI/CD

Se mantiene el `Dockerfile` actual de `ms-continuum` sin cambios estructurales (Python 3.12.8-slim-bookworm, gunicorn + uvicorn worker, `PORT=8080`) — el orden de capas (`COPY requirements.txt` + `pip install` antes de `COPY . .`) ya es correcto.

Se agrega `cloudbuild.yaml` versionado en el repo, pensado para conectarse al mismo trigger de Cloud Build que la función "Continuous Deployment" de Cloud Run ya crea, pero con caché de capas real:

1. Intentar traer la imagen `:latest` previa desde Artifact Registry como caché (`docker pull ... || true`, no falla el build si es la primera vez).
2. `docker build --cache-from <imagen previa> -t <nueva imagen> .`
3. Ejecutar `pytest` sobre `tests/unit/` como gate — si fallan los tests, no se publica ni despliega la imagen.
4. Push de la imagen a Artifact Registry.
5. `gcloud run deploy` con la nueva imagen.

Efecto esperado: un cambio que solo toca código de aplicación (no `requirements.txt`) reutiliza la capa de dependencias ya instalada, evitando la reinstalación completa de pip en cada despliegue.

## Testing

`tests/unit/` espeja uno a uno la estructura de `modules/`. Prioridad de cobertura: `domain` (entidades puras, sin mocks) > `application` (servicios con los ports mockeados) > `infrastructure` (se prueba lo mínimo, mockeando Mongo/servicios externos). Se usa `pytest` + `pytest-asyncio`. El módulo de ejemplo `tareas` incluye un test de `domain` y uno de `application` como referencia mínima a replicar en cada módulo nuevo.

## `.claude/*.md`

Adaptados desde `UltimateBackend/.claude`, con estos cambios respecto al original:

- Se excluyen: `MOONMODELER.md` (herramienta específica de modelado que no aplica aquí) y los `.md` de módulos de negocio específicos de CEMP (`USUARIOS.md`, `ENCUESTAS.md`, etc.) y las revisiones históricas en `reviews/`.
- `ARCHITECTURE.md`: se quita la sección de convivencia con código legacy (`modules_legacy/`, `routers/`, `services/`) ya que la plantilla nace 100% hexagonal, sin zona legacy.
- `STACK.md`: se mantiene el stack (FastAPI + Motor + Pydantic + Uvicorn/Gunicorn + pytest, GCP Secret Manager, patrón `Annotated + Depends`), agregando el detalle del flujo de despliegue vía `cloudbuild.yaml` + Cloud Run Continuous Deployment.
- `CONVENTIONS.md`, `TEMPLATE.md`, `TESTING.md`, `WORKFLOW.md`, `SOLID_CHECKLIST.md`, `API.md`, `MONGODB.md`, `MONGODB_MODELING.md`, `MONGODB_QUERIES.md`: se mantienen sin cambios de fondo, solo revisados para quitar cualquier referencia específica a CEMP o a `UltimateBackend`.
- `CLAUDE.md` en la raíz del repo actúa como entry point: reglas críticas + tabla de índice hacia los `.md` de `.claude/`, igual que en `UltimateBackend`.

## Desarrollo local

- `docker-compose.yml` levanta una instancia de MongoDB local para desarrollo, sin depender de Secret Manager ni de un proyecto GCP real.
- `.env.example` documenta las variables necesarias (`MONGO_URL`, `MONGO_DB`, `GCP_PROJECT_ID`, `MONGO_CERT_SECRET_NAME`, `GOOGLE_CLOUD_RUN_AUDIENCE`, `ENTORNO`, `SYSTEM_NAME`, etc.).
- `README.md` documenta: cómo correr localmente (`uvicorn main:app --reload` contra el Mongo de `docker-compose`), cómo correr los tests (`pytest`), y cómo construir/probar la imagen Docker localmente antes de depender del pipeline de Cloud Build.

## Criterios de éxito

- Un desarrollador puede clonar el repo, renombrar el módulo `tareas` a su primer módulo real, y tener un microservicio corriendo local y desplegado en Cloud Run sin tener que copiar manualmente código de otros repos (`ms-continuum`, `UltimateBackend`).
- Claude Code, al abrir el repo, encuentra `CLAUDE.md` + `.claude/*.md` con las convenciones completas y puede aplicar el `WORKFLOW.md` de 4 fases para construir un módulo nuevo sin necesitar contexto adicional del usuario.
- Un cambio de solo código (sin tocar `requirements.txt`) se despliega sin reinstalar dependencias pip desde cero.

