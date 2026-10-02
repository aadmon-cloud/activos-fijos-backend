# Contexto IA del proyecto

Este directorio concentra el contexto reutilizable para asistentes de IA en un formato neutral.
La idea es que estos archivos sirvan igual para Claude, GPT, Gemini, Copilot u otros agentes que puedan leer Markdown.

## Principios de diseno

- Una idea principal por archivo.
- El contexto estable va aqui; el detalle profundo vive en `docs/`.
- Los archivos especificos por proveedor deben enlazar esta carpeta, no duplicarla.
- Si dos documentos entran en conflicto, la prioridad es:
  1. Codigo fuente
  2. `README.md`
  3. `docs/ai/`
  4. archivos adaptadores como `AGENTS.md` o `CLAUDE.md`

## Orden recomendado de lectura

1. [01_sistema_y_alcance.md](01_sistema_y_alcance.md)
2. [02_arquitectura_y_reglas.md](02_arquitectura_y_reglas.md)
3. [03_modulos_y_flujos.md](03_modulos_y_flujos.md)
4. [04_convenciones_de_implementacion.md](04_convenciones_de_implementacion.md)
5. [05_operacion_y_entorno.md](05_operacion_y_entorno.md)
6. [06_playbook_nuevo_modulo.md](06_playbook_nuevo_modulo.md)

## Que leer segun la tarea

- Nueva feature: `01`, `02`, `03`, `04`
- Corregir bug: `01`, `02`, `05`
- Crear un modulo nuevo: `02`, `04`, `06`
- Replicar esta arquitectura en otro backend: `02`, `06` y [docs/arquitectura_hexagonal.md](../arquitectura_hexagonal.md)
- Cambios en persistencia Mongo: `05`, [docs/mongo/modelado_y_consultas.md](../mongo/modelado_y_consultas.md) y [docs/mongo/gestion_de_schemas.md](../mongo/gestion_de_schemas.md)

## Relacion con otros archivos

- `AGENTS.md`: adaptador para herramientas que leen instrucciones globales desde la raiz.
- `CLAUDE.md`: puede existir como adaptador especifico, pero no deberia ser la unica fuente de verdad.
- `docs/arquitectura_hexagonal.md`: explicacion completa de la arquitectura y sus decisiones.
- `docs/mongo/modelado_y_consultas.md`: reglas practicas de modelado, consultas y uso de pipelines.
- `docs/mongo/gestion_de_schemas.md`: versionado, validadores e indices de Mongo.

## Documentos profundos recomendados

- Si la tarea toca capas, dependencias, `shared/` o modularizacion: [docs/arquitectura_hexagonal.md](../arquitectura_hexagonal.md)
- Si la tarea toca consultas, agregaciones o builders de Mongo: [docs/mongo/modelado_y_consultas.md](../mongo/modelado_y_consultas.md)
- Si la tarea toca colecciones, validadores o sincronizacion de indices: [docs/mongo/gestion_de_schemas.md](../mongo/gestion_de_schemas.md)

## Regla de mantenimiento

Actualiza estos archivos cuando cambie alguna de estas piezas:

- modulos del negocio
- reglas de dependencia entre capas
- convenciones de creacion de modulos
- autenticacion, entorno o runbooks
- decisiones compartidas que deban replicarse en otros servicios
