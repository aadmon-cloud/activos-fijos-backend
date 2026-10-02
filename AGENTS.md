# Guia de contexto para agentes

La fuente canonica del contexto para IA de este repositorio vive en [docs/ai/README.md](docs/ai/README.md).

## Lectura minima recomendada

1. [docs/ai/README.md](docs/ai/README.md)
2. [docs/ai/01_sistema_y_alcance.md](docs/ai/01_sistema_y_alcance.md)
3. [docs/ai/02_arquitectura_y_reglas.md](docs/ai/02_arquitectura_y_reglas.md)
4. [docs/ai/04_convenciones_de_implementacion.md](docs/ai/04_convenciones_de_implementacion.md)

## Reglas criticas del proyecto

- Arquitectura hexagonal: `infrastructure -> application -> domain`
- `domain/` y `application/` no deben importar FastAPI, Motor ni SDKs cloud
- Antes de crear algo transversal, revisar si debe vivir en `shared/`
- Cada modulo expone `register_module()` en `bootstrap.py`
- El ensamblaje principal ocurre en `shared/bootstrap/application.py`
- Todo cambio nuevo de logica debe incluir o actualizar sus pruebas unitarias en Python

## Profundizar segun la tarea

- Arquitectura: [docs/arquitectura_hexagonal.md](docs/arquitectura_hexagonal.md)
- Mongo y schemas: [docs/mongo/modelado_y_consultas.md](docs/mongo/modelado_y_consultas.md), [docs/mongo/gestion_de_schemas.md](docs/mongo/gestion_de_schemas.md)
- Operacion y entorno: [docs/ai/05_operacion_y_entorno.md](docs/ai/05_operacion_y_entorno.md)
- Replicar el patron en otro servicio: [docs/ai/06_playbook_nuevo_modulo.md](docs/ai/06_playbook_nuevo_modulo.md)

## Mantenimiento

Los archivos especificos de proveedores como `CLAUDE.md` deben actuar como adaptadores livianos y apuntar a `docs/ai/`.
No dupliques reglas de negocio o arquitectura en multiples lugares si puedes enlazar la fuente canonica.
