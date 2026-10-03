import dataclasses
from datetime import UTC, datetime

import pytest

from modules.tareas.domain.entities import Tarea


def test_tarea_se_crea_con_los_campos_esperados():
    tarea = Tarea(
        id="1",
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    assert tarea.id == "1"
    assert tarea.titulo == "Escribir el plan"
    assert tarea.completada is False


def test_tarea_es_inmutable():
    tarea = Tarea(
        id="1",
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        tarea.titulo = "otro titulo"
