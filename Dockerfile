# Imagen base de Python 3.12.8. Considera 'python:3.12.8-slim-bookworm' para menor tamaño.
FROM python:3.12.8-slim-bookworm

# Directorio de trabajo en el contenedor.
WORKDIR /app

# Deshabilita el cache de pip para builds mas limpios y rapidos.
ENV PIP_NO_CACHE_DIR=1

# Copia el archivo de requerimientos e instala las dependencias.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Asegura que los binarios de pip esten en el PATH del sistema.
# Esto es crucial para que comandos como 'gunicorn' sean encontrados.
ENV PATH="/usr/local/bin:${PATH}"

# Copia el resto de tu aplicacion al directorio de trabajo.
COPY . .
ENV PORT=8080
# Comando para iniciar la aplicacion Gunicorn con worker de Uvicorn.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080"]
