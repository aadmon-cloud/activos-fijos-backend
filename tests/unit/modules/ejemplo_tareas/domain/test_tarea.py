import pytest

from modules.ejemplo_tareas.domain.entities.tarea import Tarea
from modules.ejemplo_tareas.domain.errors import TareaYaCompletadaError, TituloTareaInvalidoError


def test_crear_tarea_con_datos_validos():
    tarea = Tarea.crear(titulo="Preparar onboarding", descripcion="Documentar el flujo.")
    assert tarea.titulo == "Preparar onboarding"
    assert tarea.descripcion == "Documentar el flujo."
    assert tarea.completada is False
    assert tarea.completada_en is None
    assert tarea.id is not None


def test_crear_tarea_sin_descripcion():
    tarea = Tarea.crear(titulo="Solo titulo")
    assert tarea.descripcion is None


def test_crear_tarea_limpia_espacios_del_titulo():
    tarea = Tarea.crear(titulo="  Mi tarea  ")
    assert tarea.titulo == "Mi tarea"


def test_crear_tarea_titulo_vacio_lanza_error():
    with pytest.raises(TituloTareaInvalidoError):
        Tarea.crear(titulo="")


def test_crear_tarea_titulo_solo_espacios_lanza_error():
    with pytest.raises(TituloTareaInvalidoError):
        Tarea.crear(titulo="   ")


def test_completar_tarea_cambia_estado():
    tarea = Tarea.crear(titulo="Revisión de código")
    completada = tarea.completar()
    assert completada.completada is True
    assert completada.completada_en is not None


def test_completar_no_muta_la_tarea_original():
    tarea = Tarea.crear(titulo="Revisión de código")
    completada = tarea.completar()
    assert tarea.completada is False
    assert completada.completada is True


def test_completar_tarea_ya_completada_lanza_error():
    tarea = Tarea.crear(titulo="Revisión de código")
    completada = tarea.completar()
    with pytest.raises(TareaYaCompletadaError):
        completada.completar()
