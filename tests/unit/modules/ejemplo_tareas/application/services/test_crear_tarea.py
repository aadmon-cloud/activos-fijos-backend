import pytest
from unittest.mock import AsyncMock

from modules.ejemplo_tareas.application.dto.crear_tarea import CrearTareaInput
from modules.ejemplo_tareas.application.services.crear_tarea import CrearTareaService
from modules.ejemplo_tareas.domain.errors import TituloTareaInvalidoError


@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    repo.guardar.side_effect = lambda tarea: tarea
    return repo


@pytest.fixture
def service(mock_repository):
    return CrearTareaService(tarea_repository=mock_repository)


async def test_crear_tarea_retorna_tarea_con_titulo(service, mock_repository):
    entrada = CrearTareaInput(titulo="Tarea de prueba")
    tarea = await service.ejecutar(entrada)
    assert tarea.titulo == "Tarea de prueba"
    assert tarea.completada is False


async def test_crear_tarea_llama_al_repositorio(service, mock_repository):
    entrada = CrearTareaInput(titulo="Tarea de prueba")
    await service.ejecutar(entrada)
    mock_repository.guardar.assert_called_once()


async def test_crear_tarea_titulo_vacio_lanza_error_antes_de_persistir(
    service, mock_repository
):
    entrada = CrearTareaInput(titulo="  ")
    with pytest.raises(TituloTareaInvalidoError):
        await service.ejecutar(entrada)
    mock_repository.guardar.assert_not_called()
