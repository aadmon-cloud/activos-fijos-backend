# Arquitectura

## Regla de dependencias (obligatoria)

```
infrastructure → application → domain
bootstrap     → infrastructure / application
```

- `domain/` — entidades y reglas de negocio. Cero imports de FastAPI, Motor, Mongo, SDKs cloud.
- `application/` — casos de uso, DTOs, puertos (ABC). Sin frameworks de transporte o persistencia.
- `infrastructure/` — implementa puertos. Aquí vive FastAPI, Motor, adaptadores externos.
- `bootstrap.py` — conecta concretos, expone `register_module(app)`.

## Estructura de un módulo

```text
modules/<modulo>/
  application/
    dto/
    ports/           ← ABCs: XxxRepositoryPort
    services/        ← CrearXxxService, ListarXxxService …
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
        schema/      ← definición versionada de colección
        pipelines/   ← builders de agregación (si aplica)
        xxx_repository.py
  bootstrap.py
```

## ¿Qué va en `shared/`?

Sí → lo usan varios módulos, no pertenece a un dominio, es infraestructura común.  
No → resuelve reglas de un único dominio, solo existe para un módulo puntual.

## Anti-patrones

- Lógica de negocio dentro de rutas FastAPI
- `application/` invocando repositorio concreto (saltarse el puerto)
- `domain/` importando Motor, FastAPI o cualquier SDK externo
- Subir algo a `shared/` "por si acaso"
- Crear `__init__.py` — el proyecto usa namespace packages (Python 3.3+)
