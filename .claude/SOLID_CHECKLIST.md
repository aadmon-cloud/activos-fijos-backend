# Checklist antes de PR

## Arquitectura

- [ ] `domain/` no importa FastAPI, Motor ni SDKs externos
- [ ] `application/` no importa frameworks de transporte o persistencia
- [ ] Los servicios dependen de puertos (ABCs), no de repositorios concretos
- [ ] La ruta FastAPI solo traduce HTTP → delega al servicio → devuelve respuesta
- [ ] No se crearon `__init__.py`

## Ubicación de código

- [ ] Lógica de negocio en `domain/` o `application/`, no en rutas
- [ ] Schemas HTTP en `infrastructure/api/schemas.py`
- [ ] Mapeo Mongo en el repositorio (o `xxx_mapper.py` si es grande)
- [ ] Antes de duplicar algo, revisé `shared/`

## API

- [ ] Cada endpoint tiene `summary=` (verbo en tercera persona)
- [ ] `responses=` documenta los errores 4xx de negocio relevantes
- [ ] No hay lógica de negocio en los handlers
- [ ] Los errores de dominio se capturan antes de llegar al cliente como 500

## MongoDB

- [ ] Índices responden a consultas concretas (prefijo `idx_`/`uq_`/`ttl_`)
- [ ] Pipeline tiene `$match` al inicio

## Tests

- [ ] Cada servicio nuevo o modificado tiene prueba unitaria
- [ ] Si se corrigió un bug: hay prueba que reproduce el caso
- [ ] Las pruebas no dependen de Mongo real
- [ ] Archivos de test en `tests/unit/modules/<modulo>/...`

## Módulo

- [ ] Si el módulo es nuevo: `register_module(app)` implementado y registrado
