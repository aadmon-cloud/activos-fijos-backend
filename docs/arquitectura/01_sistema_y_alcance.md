# Sistema y alcance

## Que es `template-fastapi-backend`

`template-fastapi-backend` es una plantilla de backend lista para usar con FastAPI y arquitectura hexagonal.
Sirve como punto de partida para nuevos servicios que necesiten una base ordenada, modular y extensible desde el primer commit.

## Proposito de la plantilla

- Proporcionar una estructura de capas clara con separacion entre dominio, aplicacion e infraestructura.
- Incluir un modulo de ejemplo (`modules/ejemplo_tareas/`) que ilustra como implementar una feature completa siguiendo las reglas de la arquitectura.
- Ofrecer piezas transversales listas en `shared/`: manejo de errores, puertos comunes, configuracion, conexion a bases de datos y arranque de la aplicacion.
- Documentar las convenciones de codigo, nombres y estructura para que los equipos puedan mantener consistencia a lo largo del tiempo.

## Que no es esta plantilla

- No es un sistema en produccion; es un punto de partida que debe adaptarse al dominio especifico de cada proyecto.
- No incluye logica de negocio real mas alla del modulo de ejemplo.
- No reemplaza las decisiones de arquitectura propias del proyecto que use la plantilla.

## Stack principal

- Python + FastAPI
- MongoDB con Motor
- Pydantic
- Uvicorn / Gunicorn

## Mapa de carpetas de alto nivel

```text
modules/      # modulos de dominio (ejemplo_tareas/ sirve de guia y referencia)
shared/       # piezas transversales: bootstrap, dominio base, puertos e infraestructura comun
config/       # configuracion y logging
docs/         # documentacion de arquitectura, decisiones y guias de implementacion
main.py       # punto de entrada
```

## Limites utiles para una IA

- Esta plantilla ya cumple la arquitectura objetivo desde el primer commit; no hay codigo legacy que migrar.
- Todos los modulos nuevos deben seguir el patron de `modules/ejemplo_tareas/`.
- Las piezas transversales viven en `shared/`; antes de crearlas ahi, verificar que realmente sean compartidas y no pertenezcan a un modulo especifico.
- El dominio y la aplicacion no deben importar FastAPI, Motor ni ninguna libreria de infraestructura.
- El ensamblaje de dependencias ocurre en `shared/bootstrap/application.py` a traves del metodo `register_module()` de cada modulo.
