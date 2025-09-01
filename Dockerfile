FROM python:3.11-slim

# 1) Instalar librerías del sistema que WeasyPrint necesita
RUN apt-get update && apt-get install -y \
    libgobject-2.0-0 libglib2.0-dev libcairo2-dev libpango1.0-dev \
    libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copiar y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copiar código
COPY . .

# 4) Puerto que Render expone
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]