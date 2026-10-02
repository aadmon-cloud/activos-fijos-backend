import io

import pandas as pd

from modules.movimientos.domain.entities.movimiento import Movimiento

_ETIQUETA_TIPO = {
    "entrada": "ENTRADA",
    "salida": "SALIDA",
    "creacion_ubicacion": "CREACIÓN DE UBICACIÓN",
    "transferencia_ubicacion": "TRANSFERENCIA ENTRE UBICACIONES",
}

_COLUMNAS = [
    "Fecha",
    "Tipo",
    "Código Producto",
    "Nombre Producto",
    "Cantidad",
    "Motivo",
    "Proveedor/Cliente",
    "Ubicación",
    "Tipo Origen",
    "Remisión",
    "Caso",
    "Notas",
    "Usuario",
]


def generar_excel(movimientos: list[Movimiento]) -> bytes:
    """Construye el `.xlsx` de exportación. Vive en infraestructura (usa
    pandas/openpyxl) — el servicio de aplicación solo devuelve entidades.

    Nota: el legacy incluía columnas "Stock Anterior"/"Stock Actual"
    calculadas desde `mov.get('stock_actual', 0)`, un campo que el documento
    de movimiento nunca guardó — esas columnas siempre mostraban 0 en
    producción. Se omiten acá en vez de reproducir un dato roto.
    """
    if not movimientos:
        df = pd.DataFrame({"Mensaje": ["No hay movimientos para exportar"]})
    else:
        df = pd.DataFrame([_fila(m) for m in movimientos], columns=_COLUMNAS)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Movimientos", index=False)
        _ajustar_columnas(writer.sheets["Movimientos"], df)
    buffer.seek(0)
    return buffer.getvalue()


def _fila(movimiento: Movimiento) -> dict:
    origen_destino = movimiento.origen_nombre or movimiento.cliente_destino or "-"
    return {
        "Fecha": movimiento.creado_por.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        "Tipo": _ETIQUETA_TIPO.get(movimiento.tipo, movimiento.tipo.upper()),
        "Código Producto": movimiento.producto_codigo or "-",
        "Nombre Producto": movimiento.producto_nombre or "-",
        "Cantidad": movimiento.cantidad,
        "Motivo": movimiento.motivo or "-",
        "Proveedor/Cliente": origen_destino,
        "Ubicación": movimiento.ubicacion or "-",
        "Tipo Origen": movimiento.tipo_origen or "-",
        "Remisión": movimiento.remision or "-",
        "Caso": movimiento.caso or "-",
        "Notas": movimiento.notas or "-",
        "Usuario": movimiento.creado_por.nombre,
    }


def _ajustar_columnas(worksheet, df: pd.DataFrame) -> None:
    for indice, columna in enumerate(df.columns):
        largo_maximo = len(str(columna))
        if len(df) > 0:
            largo_maximo = max(largo_maximo, df[columna].astype(str).map(len).max())
        worksheet.column_dimensions[chr(65 + indice)].width = min(largo_maximo + 2, 50)
