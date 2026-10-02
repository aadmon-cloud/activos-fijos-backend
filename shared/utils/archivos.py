import mimetypes

# Lista de mimes soportados por Gemini para visión
MIMES_SOPORTADOS = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif"
]

def obtener_mime_type(nombre_archivo: str) -> str:
    """
    Determina el mime_type basado en la extensión del archivo.
    """
    mime, _ = mimetypes.guess_type(nombre_archivo)
    
    if not mime or mime not in MIMES_SOPORTADOS:
        return "application/octet-stream" 
        
    return mime