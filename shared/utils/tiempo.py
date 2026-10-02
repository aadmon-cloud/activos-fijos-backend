def formatear_minutos_texto(minutos: float | int) -> str:
    """
    Convierte una cantidad de minutos a un texto legible para personas.

    Ejemplos:
    - 5 -> "00 horas y 05 minutos"
    - 65 -> "01 hora y 05 minutos"
    - 120 -> "02 horas y 00 minutos"
    """
    if minutos is None:
        raise ValueError("El valor de minutos no puede ser nulo")

    total_minutos = int(round(minutos))

    if total_minutos < 0:
        raise ValueError("El valor de minutos no puede ser negativo")

    horas, minutos_restantes = divmod(total_minutos, 60)

    horas_texto = "hora" if horas == 1 else "horas"
    minutos_texto = "minuto" if minutos_restantes == 1 else "minutos"

    return f"{horas:02d} {horas_texto} y {minutos_restantes:02d} {minutos_texto}"