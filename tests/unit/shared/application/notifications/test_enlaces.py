from shared.application.notifications.enlaces import MARCADOR_URL_APP, enlace, resolver_enlaces


def test_enlace_antepone_el_marcador():
    assert enlace("/movimientos/detalle?id=1") == f"{MARCADOR_URL_APP}/movimientos/detalle?id=1"


def test_con_url_base_reemplaza_el_marcador_y_quita_la_barra_final():
    cuerpo = f"Hola\n\nVer: {enlace('/solicitudes/detalle?id=9')}"

    assert resolver_enlaces(cuerpo, "https://activos.example.org/") == (
        "Hola\n\nVer: https://activos.example.org/solicitudes/detalle?id=9"
    )


def test_sin_url_base_quita_las_lineas_con_enlace_para_no_mandar_un_enlace_roto():
    cuerpo = f"Se aprobo la solicitud.\n\nVer el movimiento: {enlace('/movimientos/detalle?id=1')}"

    resultado = resolver_enlaces(cuerpo, None)

    assert resultado == "Se aprobo la solicitud."
    assert MARCADOR_URL_APP not in resultado


def test_un_cuerpo_sin_enlace_queda_igual():
    assert resolver_enlaces("Solo texto", "https://x.org") == "Solo texto"
    assert resolver_enlaces("Solo texto", None) == "Solo texto"
