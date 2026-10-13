ASUNTO_MAXIMO = 200
CUERPO_MAXIMO = 5000
DESTINATARIOS_MAXIMO = 200
DETALLE_MAXIMO = 300


def limpiar_asunto(asunto: str) -> str:
    """Una sola linea y de largo acotado: un salto de linea en el asunto permitiria inyectar cabeceras de
    correo (OWASP A03)."""
    return " ".join((asunto or "").split())[:ASUNTO_MAXIMO]


def limpiar_cuerpo(cuerpo: str) -> str:
    return (cuerpo or "").strip()[:CUERPO_MAXIMO]


def acotar_detalle(detalle: str) -> str:
    return (detalle or "").strip()[:DETALLE_MAXIMO]
