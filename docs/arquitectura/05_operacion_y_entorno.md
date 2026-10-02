# Operacion y entorno

## Variables de entorno principales

- `GCP_PROJECT_ID`
- `MONGO_URL`
- `MONGO_DB`
- `MONGO_CERT_SECRET_NAME`

## Arranque local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Endpoints utiles del servicio

- `http://localhost:8080/`
- `http://localhost:8080/docs`
- `http://localhost:8080/redoc`

## Consideraciones operativas

- En el arranque, la app conecta a Mongo y obtiene secretos desde GCP.
- Para correr localmente hacen falta credenciales validas de GCP con acceso a Secret Manager.
- El `shared` nuevo no asume que CEMP corre dentro de Cloud Run.
- La invocacion saliente a servicios externos puede seguir usando GCP o Cloud Run como integracion, pero eso no define el modelo de despliegue del backend.
- El lifecycle principal se monta desde `shared/bootstrap/application.py` y `main.py`.

## Sincronizacion de schemas Mongo

```powershell
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --dry-run
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --only proyectos
```

Recomendacion:

1. Ejecutar primero con `--dry-run`
2. Revisar validators e indices planeados
3. Ejecutar sin `--dry-run` solo cuando el resultado sea correcto

## Documentacion complementaria

- [../arquitectura_hexagonal.md](../arquitectura_hexagonal.md)
- [../mongo/modelado_y_consultas.md](../mongo/modelado_y_consultas.md)
- [../mongo/gestion_de_schemas.md](../mongo/gestion_de_schemas.md)
