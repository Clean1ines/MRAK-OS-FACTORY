# ==================== STAGE 1: Build Frontend ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Копируем только package файлы (кэш зависимостей)
COPY frontend/package*.json ./
RUN npm ci

# Копируем исходники и собираем
COPY frontend/ ./
RUN npm run build

# ==================== STAGE 2: Python Runtime ====================
FROM python:3.10-slim

WORKDIR /app

# Python зависимости
COPY requirements-prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем бэкенд
COPY . .

# Копируем собранный фронтенд из Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/static

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]