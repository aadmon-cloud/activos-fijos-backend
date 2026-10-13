def _a_diccionario(grupos: list[dict]) -> dict[str, int]:
    return {grupo["_id"]: grupo["cantidad"] for grupo in grupos if grupo["_id"] is not None}


async def contar_y_agrupar(coleccion, *campos_agrupar: str) -> tuple[int, dict[str, dict[str, int]]]:
    """Un solo $facet que cuenta el total de la coleccion y agrupa por cada campo dado.

    Retorna (total, {campo: {valor: cantidad}}). Usado por los 5 adaptadores de resumen del
    dashboard para no repetir la misma forma de pipeline en cada uno.
    """
    facet = {"total": [{"$count": "cantidad"}]}
    for campo in campos_agrupar:
        facet[campo] = [{"$group": {"_id": f"${campo}", "cantidad": {"$sum": 1}}}]

    resultado = await coleccion.aggregate([{"$facet": facet}]).to_list(length=1)
    datos = resultado[0] if resultado else {clave: [] for clave in facet}

    total = datos["total"][0]["cantidad"] if datos["total"] else 0
    agrupados = {campo: _a_diccionario(datos[campo]) for campo in campos_agrupar}
    return total, agrupados
