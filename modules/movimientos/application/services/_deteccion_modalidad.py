def detectar_modalidad_reserva(datos_adicionales: dict) -> str:
    """Misma heurística que el legacy: `tipo` explícito, o `kitNombre` como
    señal de que en realidad es una reserva de kit sin `tipo` seteado."""
    modalidad = datos_adicionales.get("tipo") or "normal"
    if modalidad == "normal" and datos_adicionales.get("kitNombre"):
        modalidad = "kit"
    return modalidad
