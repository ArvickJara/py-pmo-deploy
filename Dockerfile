# Dockerfile para PMO Python API
# Incluye todas las dependencias del sistema

FROM python:3.11-slim

# Etiquetas
LABEL maintainer="PMO Gore"
LABEL description="API Python para procesamiento de PDFs con YOLO y OCR"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    # Poppler (para pdf2image)
    poppler-utils \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Otras utilidades
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 pmouser && \
    mkdir -p /app /app/temp /app/logs /app/models && \
    chown -R pmouser:pmouser /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cachear mejor)
COPY --chown=pmouser:pmouser requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copiar el código de la aplicación
COPY --chown=pmouser:pmouser . .

# Crear directorios necesarios
RUN mkdir -p temp logs models && \
    chmod 777 temp logs

# Cambiar al usuario no-root
USER pmouser

# Exponer puerto
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Comando por defecto
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
