TAMANO_MAXIMO_FOTO_BYTES = 5 * 1024 * 1024

_FIRMA_JPEG = b"\xff\xd8\xff"
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
_FIRMA_RIFF = b"RIFF"
_FIRMA_WEBP = b"WEBP"
_INICIO_FORMATO_WEBP = 8
_FIN_FORMATO_WEBP = 12


def detectar_tipo_imagen(contenido: bytes) -> str | None:
    """Tipo MIME segun los primeros bytes del archivo; None si no es JPEG, PNG ni WebP.

    No se confia en el Content-Type que declara el cliente: lo controla quien envia.
    """
    if contenido.startswith(_FIRMA_JPEG):
        return "image/jpeg"
    if contenido.startswith(_FIRMA_PNG):
        return "image/png"
    if (
        contenido.startswith(_FIRMA_RIFF)
        and contenido[_INICIO_FORMATO_WEBP:_FIN_FORMATO_WEBP] == _FIRMA_WEBP
    ):
        return "image/webp"

    return None


def ruta_foto(id_activo: str) -> str:
    """Ruta interna (autenticada) desde donde se descarga la foto de un activo."""
    return f"/api/activos/{id_activo}/foto"
