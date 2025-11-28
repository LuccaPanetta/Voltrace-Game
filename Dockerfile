FROM python:3.10-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev

# Crear un entorno virtual (venv) para aislar las librerías
RUN python -m venv /opt/venv

# Activar el entorno virtual en el PATH
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim

WORKDIR /app

# Instalar SOLO las librerías de sistema necesarias para correr
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* # ^^^ Esto borra la caché de apt para ahorrar espacio

# Copiar el entorno virtual con las librerías instaladas desde la etapa 'builder'
COPY --from=builder /opt/venv /opt/venv

# Activar el entorno virtual
ENV PATH="/opt/venv/bin:$PATH"

# Copiar el código de la aplicación
COPY . .

# Configuración de ejecución
EXPOSE 5000
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]

# Healthcheck 
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1