from unittest.mock import AsyncMock

import pytest

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.domain.entities import Tarea
from modules.tareas.domain.errors import TituloTareaVacioError


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.guardar.side_effect = lambda tarea: Tarea(
        id="1",
        titulo=tarea.titulo,
        completada=tarea.completada,
        fecha_creacion=tarea.fecha_creacion,
    )
    return mock


async def test_crear_tarea_guarda_la_entidad_con_titulo_recortado(repositorio_mock):
    service = CrearTareaService(repositorio_mock)

    resultado = await service.ejecutar(CrearTareaDTO(titulo="  Escribir el plan  "))

    assert resultado.id == "1"
    assert resultado.titulo == "Escribir el plan"
    assert resultado.completada is False
    repositorio_mock.guardar.assert_called_once()
    tarea_guardada = repositorio_mock.guardar.call_args.args[0]
    assert tarea_guardada.titulo == "Escribir el plan"


async def test_crear_tarea_lanza_error_si_el_titulo_esta_vacio(repositorio_mock):
    service = CrearTareaService(repositorio_mock)

    with pytest.raises(TituloTareaVacioError):
        await service.ejecutar(CrearTareaDTO(titulo="   "))

    repositorio_mock.guardar.assert_not_called()
