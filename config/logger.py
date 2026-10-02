import logging
import sys

def configurar_logging():
    """
    Configura el formato y nivel de los logs para toda la aplicación.
    """
    # Formato profesional: Tiempo | Nivel | Archivo/Modulo | Mensaje
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para consola (Stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formato)

    # Configuración Global
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # <--- AQUÍ HABILITAS EL DEBUG
    
    # Limpiamos handlers previos para evitar duplicados al recargar
    if root_logger.handlers:
        root_logger.handlers = []
    
    root_logger.addHandler(console_handler)

    # (Opcional) Callar un poco a librerías ruidosas
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)