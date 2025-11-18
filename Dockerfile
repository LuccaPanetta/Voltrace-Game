# 1. Usar una imagen base oficial de Python
FROM python:3.10-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar CURL para que funcione el Healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 3. Copiar el archivo de requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. Copiar TODO el resto del código del proyecto al contenedor
COPY . .

# 5. Exponer el puerto
EXPOSE 5000

# 6. El comando para iniciar la aplicación
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]

# 7. HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1