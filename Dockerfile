# Usar una imagen base de Python oficial y liviana
FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc en el disco y asegurar que los logs se emitan directamente a stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para construir ciertos paquetes si es necesario
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar primero el archivo de requerimientos para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del chatbot al contenedor
COPY . .

# Crear un usuario no root por motivos de seguridad y otorgar permisos
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    chown -R appuser:appgroup /app

# Cambiar al usuario no root
USER appuser

# Exponer el puerto en el que corre FastAPI
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
