from modules.notificaciones.domain.errors import (
    NotificacionNoEncontradaError,
    NotificacionNoReenviableError,
)
from modules.notificaciones.domain.limites import (
    ASUNTO_MAXIMO,
    CUERPO_MAXIMO,
    DETALLE_MAXIMO,
    acotar_detalle,
    limpiar_asunto,
    limpiar_cuerpo,
)
from shared.domain.errors import ErrorCategory


def test_el_asunto_queda_en_una_sola_linea_para_evitar_la_inyeccion_de_cabeceras():
    asunto = "Hola\r\nBcc: victima@x.com\nSubject: otro"

    assert limpiar_asunto(asunto) == "Hola Bcc: victima@x.com Subject: otro"
    assert "\n" not in limpiar_asunto(asunto) and "\r" not in limpiar_asunto(asunto)


def test_el_asunto_se_acota_y_tolera_vacio_o_none():
    assert len(limpiar_asunto("x" * (ASUNTO_MAXIMO + 50))) == ASUNTO_MAXIMO
    assert limpiar_asunto("") == ""
    assert limpiar_asunto(None) == ""


def test_el_cuerpo_se_recorta_y_se_acota():
    assert limpiar_cuerpo("  Hola\n\n ") == "Hola"
    assert len(limpiar_cuerpo("y" * (CUERPO_MAXIMO + 10))) == CUERPO_MAXIMO


def test_el_detalle_se_acota():
    assert len(acotar_detalle("z" * (DETALLE_MAXIMO + 10))) == DETALLE_MAXIMO
    assert acotar_detalle(None) == ""


def test_notificacion_no_encontrada_tiene_code_y_category():
    error = NotificacionNoEncontradaError("n1")

    assert error.code == "NTF-001"
    assert error.category == ErrorCategory.NOT_FOUND


def test_notificacion_no_reenviable_tiene_code_y_category():
    error = NotificacionNoReenviableError("n1")

    assert error.code == "NTF-002"
    assert error.category == ErrorCategory.BUSINESS_RULE
