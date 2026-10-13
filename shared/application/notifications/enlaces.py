# Los modulos escriben los correos sin saber la direccion del frontend: ponen este marcador y el sistema
# de notificaciones lo reemplaza por la direccion configurada (o quita la linea si no hay ninguna).
MARCADOR_URL_APP = "{{URL_APP}}"


def enlace(ruta: str) -> str:
    """Enlace a una pagina de la aplicacion, p. ej. enlace("/movimientos/detalle?id=1")."""
    return f"{MARCADOR_URL_APP}{ruta}"


def resolver_enlaces(cuerpo: str, url_base: str | None) -> str:
    """Reemplaza el marcador por la direccion de la aplicacion; sin direccion, quita las lineas con enlace
    para no mandar un enlace roto."""
    if url_base:
        return cuerpo.replace(MARCADOR_URL_APP, url_base.rstrip("/"))

    lineas = [linea for linea in cuerpo.splitlines() if MARCADOR_URL_APP not in linea]

    return "\n".join(lineas).strip()
