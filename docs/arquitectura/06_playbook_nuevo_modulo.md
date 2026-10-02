# Playbook nuevo modulo

Este archivo cumple dos objetivos:

- servir como checklist para agregar un modulo nuevo en `ms-continuum`
- funcionar como plantilla reusable para otros backends hexagonales similares

## Secuencia recomendada

1. Definir el limite del dominio y el nombre del modulo
2. Modelar entidades y errores de negocio
3. Crear DTOs de entrada y salida
4. Definir puertos de repositorio o integracion
5. Implementar servicios de aplicacion
6. Implementar persistencia e interfaz HTTP
7. Registrar el modulo en el bootstrap
8. Documentar endpoints, auth y consideraciones operativas

## Estructura base

```text
modules/
  nombre_modulo/
    application/
      dto/
      ports/
      services/
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
          schema/
    bootstrap.py
```

## Checklist de diseno

- La entidad principal esta en `domain/entities/`
- Las reglas de negocio viven fuera de FastAPI
- Los servicios dependen de puertos
- La persistencia concreta implementa puertos
- Las rutas delegan al servicio y solo traducen HTTP
- El modulo expone `register_module(app)`
- El registro global se hace en `shared/bootstrap/application.py`
- No se crean archivos `__init__.py` — el proyecto usa namespace packages de Python 3.3+
- Cada endpoint tiene `summary=` y `responses=` con los errores 4xx de negocio relevantes
- Los servicios con logica no obvia tienen docstring en `ejecutar()` con seccion `Raises:`

## Decision de ubicacion

- Si la regla aplica solo a un dominio: `modules/<modulo>/`
- Si la usan varios modulos: evaluar `shared/`
- Si es una integracion externa reusable: normalmente `shared/infrastructure/`

## Plantilla reusable para otros servicios

Cuando repliques esta arquitectura en otro backend, intenta mantener:

- misma separacion `domain/application/infrastructure/bootstrap`
- convencion de puertos en `application/ports/`
- composition root explicito
- modulo compartido para infraestructura transversal
- runbooks pequenos y enlazados en vez de una sola guia enorme

## Archivos de contexto IA recomendados para cualquier backend

Si vas a repetir este enfoque en otros proyectos, la base minima es:

1. `docs/ai/README.md`
2. `docs/ai/01_sistema_y_alcance.md`
3. `docs/ai/02_arquitectura_y_reglas.md`
4. `docs/ai/04_convenciones_de_implementacion.md`
5. `docs/ai/05_operacion_y_entorno.md`

Con eso ya tienes una capa canonica y neutral para casi cualquier modelo.

## Referencias de apoyo

- [../arquitectura_hexagonal.md](../arquitectura_hexagonal.md) para validar la separacion entre capas y el uso de `shared/`
- [../mongo/modelado_y_consultas.md](../mongo/modelado_y_consultas.md) si el modulo nuevo requiere consultas complejas o pipelines
- [../mongo/gestion_de_schemas.md](../mongo/gestion_de_schemas.md) si el modulo nuevo agrega colecciones, indices o validadores
