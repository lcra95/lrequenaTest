# Utiliza la imagen oficial de Python como base
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos e instalar dependencias
COPY ./lrequenaTest/requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY ./lrequenaTest .

# Exponer el puerto en el que FastAPI se ejecutará
EXPOSE 8000

# Comando para ejecutar la aplicación usando Uvicorn en producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
