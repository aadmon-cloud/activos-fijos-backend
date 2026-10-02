# Testing

## Regla principal

Todo cambio de negocio o de aplicación debe incluir pruebas unitarias. Sin excepción documentada explícita.

## Estructura de carpetas

```text
tests/
  unit/
    modules/
      <modulo>/
        application/
          services/
            test_crear_xxx.py
        domain/
    shared/
      application/
      domain/
  integration/
    modules/
    shared/
  fixtures/
  conftest.py
```

`tests/unit/` espeja `modules/` y `shared/`. Las pruebas no viven dentro de los módulos.

## Qué testear con prioridad

1. `domain/` — entidades, reglas de negocio, errores de dominio
2. `application/services/` — casos de uso, lógica de orquestación
3. `infrastructure/` — solo si hay lógica no trivial en mapeos o pipelines

## Qué NO mockear

- Lógica propia del módulo
- Reglas de dominio

## Qué SÍ mockear / no depender de

- MongoDB real
- FastAPI levantado
- Servicios externos (GCP, Redis, etc.)

Los repositorios se mockean con implementaciones en memoria o MagicMock en pruebas unitarias.

## Convención de nombres

```
test_<componente>.py          → archivo
test_<comportamiento>         → función de test
```

Ejemplo:
```
modules/tareas/application/services/crear_tarea.py
→ tests/unit/modules/tareas/application/services/test_crear_tarea.py
```

## Patrón de test de servicio

```python
# tests/unit/modules/xxx/application/services/test_crear_xxx.py
import pytest
from unittest.mock import AsyncMock
from modules.xxx.application.services.crear_xxx import CrearXxxService
from modules.xxx.application.dto.crear_xxx_dto import CrearXxxDTO

@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.guardar.return_value = None
    return mock

@pytest.mark.asyncio
async def test_crear_xxx_guarda_entidad(repositorio_mock):
    service = CrearXxxService(repositorio_mock)
    dto = CrearXxxDTO(nombre="test")
    await service.ejecutar(dto)
    repositorio_mock.guardar.assert_called_once()
```

## Cuándo hacer integración vs unitaria

- Unitaria: lógica de dominio y aplicación (sin infra)
- Integración: cuando la prueba necesita Mongo real, comportamiento HTTP, o flujo completo
