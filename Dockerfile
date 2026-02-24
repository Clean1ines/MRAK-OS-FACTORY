FROM python:3.10-slim

WORKDIR /app

# Установить Node.js для сборки фронтенда
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements-prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копировать весь проект
COPY . .

# Собрать фронтенд
WORKDIR /app/frontend
RUN npm ci
RUN npm run build

# Настроить статику
WORKDIR /app
RUN mkdir -p static
RUN cp -r frontend/dist/* static/

EXPOSE 8000

# Запустить сервер
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]