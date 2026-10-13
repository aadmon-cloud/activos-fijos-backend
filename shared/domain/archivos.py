_FIRMA_JPEG = b"\xff\xd8\xff"
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
_FIRMA_RIFF = b"RIFF"
_FIRMA_WEBP = b"WEBP"
_INICIO_FORMATO_WEBP = 8
_FIN_FORMATO_WEBP = 12
_FIRMA_PDF = b"%PDF-"


def detectar_tipo_archivo(contenido: bytes) -> str | None:
    """Tipo MIME segun los primeros bytes del archivo; None si no es un formato soportado.

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
    if contenido.startswith(_FIRMA_PDF):
        return "application/pdf"

    return None
