# Arquitectura y reglas

## Estilo arquitectonico

El proyecto sigue arquitectura hexagonal (`ports and adapters`).
La separacion principal es:

- `domain`: entidades y reglas puras de negocio
- `application`: casos de uso, DTOs y puertos
- `infrastructure`: HTTP, persistencia y adaptadores externos
- `bootstrap`: ensamblaje y registro de dependencias

## Direccion obligatoria de dependencias

```text
infrastructure -> application -> domain
bootstrap -> infrastructure/application
```

Reglas practicas:

- `domain/` no importa FastAPI, Motor, Mongo ni SDKs cloud.
- `application/` no importa frameworks de transporte o persistencia.
- `infrastructure/` implementa puertos definidos en `application/`.
- `bootstrap/` conecta concretos y registra el modulo en la app.

## Como se aplica en este repo

- Cada modulo de negocio en `modules/` replica la misma estructura base.
- `shared/` contiene piezas realmente transversales, como persistencia comun, invocacion de servicios externos o utilidades.
- El composition root principal esta en `shared/bootstrap/application.py`.

## Patrones esperados

- Use case / service por accion de negocio
- Repository port en `application/ports/`
- Repositorio Mongo en `infrastructure/persistence/mongo/`
- Dependency injection con `Depends(...)`
- `register_module(app)` por modulo

## Cuando algo debe ir en `shared`

Debe ir en `shared/` si:

- lo usan varios modulos
- no pertenece a un dominio funcional especifico
- es infraestructura comun

No debe ir en `shared/` si:

- resuelve reglas de un unico dominio
- solo existe para un modulo puntual
- se esta subiendo a compartido "por si acaso"

## Anti-patrones a evitar

- Mezclar reglas de negocio dentro de rutas FastAPI
- Saltarse puertos e invocar persistencia concreta desde `application/`
- Meter dependencias de infraestructura en `domain/`
- Duplicar utilidades ya resueltas en `shared/`

## Referencia profunda

Para la explicacion completa de la arquitectura y sus convenciones, revisar [../arquitectura_hexagonal.md](../arquitectura_hexagonal.md).

Complementa esta lectura con:

- [04_convenciones_de_implementacion.md](04_convenciones_de_implementacion.md) para ver la forma esperada de construir codigo nuevo
- [06_playbook_nuevo_modulo.md](06_playbook_nuevo_modulo.md) para repetir este patron en otros servicios
