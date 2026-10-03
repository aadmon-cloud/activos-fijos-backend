# Testing

## Regla principal

Todo cambio de negocio o de aplicación debe incluir pruebas unitarias. Sin excepción documentada explícita.

## Estructura de carpetas

```text
tests/
  unit/
    modules/
      <modulo>/
        domain/
        application/
          services/
            test_crear_xxx.py
        infrastructure/
    shared/
      application/
      domain/
      infrastructure/
  conftest.py
```

`tests/unit/` espeja `modules/` y `shared/`. Las pruebas no viven dentro de los módulos.

## Qué testear con prioridad

1. `domain/` — entidades, reglas de negocio, errores de dominio
2. `application/services/` — casos de uso, lógica de orquestación
3. `infrastructure/` — solo si hay lógica no trivial en mapeos (ej. `_doc_a_entidad`)

## Qué NO mockear

- Lógica propia del módulo
- Reglas de dominio

## Qué SÍ mockear / no depender de

- MongoDB real
- Servicios externos (GCP Secret Manager, llamadas a otros Cloud Run)

Los repositorios se mockean con `AsyncMock`/`MagicMock` o implementaciones en memoria en pruebas unitarias de `application/`.

## Convención de nombres

```
test_<componente>.py          → archivo
test_<comportamiento>         → función de test
```

## Patrón de test de servicio

```python
# tests/unit/modules/xxx/application/services/test_crear_xxx.py
from unittest.mock import AsyncMock

import pytest

from modules.xxx.application.services.crear_xxx import CrearXxxService
from modules.xxx.application.dto.crear_xxx_dto import CrearXxxDTO


@pytest.fixture
def repositorio_mock():
    return AsyncMock()


async def test_crear_xxx_guarda_entidad(repositorio_mock):
    service = CrearXxxService(repositorio_mock)
    await service.ejecutar(CrearXxxDTO(nombre="test"))
    repositorio_mock.guardar.assert_called_once()
```

Referencia completa y funcional: `tests/unit/modules/tareas/`.
