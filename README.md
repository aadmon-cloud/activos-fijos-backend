# fastapi-cloud-run — Plantilla base para microservicios en Cloud Run

Plantilla de referencia para iniciar microservicios FastAPI desplegados en
Cloud Run, con arquitectura hexagonal (`domain → application → infrastructure`).
Incluye un modulo de ejemplo (`tareas`) funcional de punta a punta.

## Requisitos

- Python 3.12
- Docker (para MongoDB local y para construir la imagen)

## Desarrollo local

```bash
# 1. Levantar MongoDB local
docker compose up -d mongo

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements-dev.txt

# 3. Configurar variables de entorno
copy .env.example .env      # Windows (cp en Linux/Mac)
# .env ya viene con ENTORNO=local y MONGO_URL apuntando al contenedor local

# 4. Arrancar la aplicacion
python main.py
```

Endpoints disponibles en `http://localhost:8080/docs`.

## Tests

```bash
pytest
```

## Construir y probar la imagen Docker localmente

```bash
docker build -t fastapi-cloud-run-template .
docker run --rm -p 8080:8080 --env-file .env fastapi-cloud-run-template
```

Nota: para correr contra Mongo local desde el contenedor, cambia
`MONGO_URL` en `.env` a `mongodb://host.docker.internal:27017`.

## Despliegue

El despliegue a Cloud Run se hace vía el trigger de Cloud Build ya configurado
con "Continuous Deployment" nativo de Cloud Run, usando el `cloudbuild.yaml`
versionado en este repo (ver seccion correspondiente). Este pipeline corre los
tests como gate y reutiliza el cache de capas Docker para que un cambio de
solo codigo no reinstale las dependencias desde cero.

### Variables de entorno del servicio Cloud Run

`config/settings.py` exige varias variables sin valor por defecto, y se
instancian al arrancar la app (`settings = Settings()`), asi que el servicio
falla al iniciar si no estan configuradas. El `gcloud run deploy --image ...`
de `cloudbuild.yaml` no las setea (a proposito): asume que el servicio ya
quedo configurado una vez via "Continuous Deployment" en la consola de Cloud
Run, y solo despliega una imagen nueva sobre esa configuracion existente.

Por eso, antes o durante el primer despliegue (por ejemplo, al configurar por
primera vez "Continuous Deployment" en la consola de Cloud Run), hay que
setear en el servicio (via consola o `--set-env-vars`/`--set-secrets`, no en
este repo):

- `GCP_PROJECT_ID` (obligatoria)
- `MONGO_URL` (obligatoria)
- `MONGO_DB` (obligatoria)
- `ENTORNO` (recomendable definirla explicitamente, p.ej. `cloud`, `staging`, `production`)
- `MONGO_CERT_SECRET_NAME` (obligatoria cuando `ENTORNO != "local"`)
- `GOOGLE_CLOUD_RUN_AUDIENCE` y `SYSTEM_NAME` (opcionales, segun uso de invocacion servicio a servicio)

## Estructura del proyecto

Ver `.claude/ARCHITECTURE.md` para el detalle de capas y convenciones, y
`.claude/TEMPLATE.md` para el checklist de como agregar un modulo nuevo
(usando `modules/tareas/` como referencia).

## Como agregar un modulo nuevo

Seguir `.claude/WORKFLOW.md` (flujo de 4 fases) y `.claude/TEMPLATE.md`
(checklist de construccion), usando `modules/tareas/` como plantilla a
copiar y renombrar.
