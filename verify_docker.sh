#!/bin/bash
set -e

echo "🔨 Building Docker image..."
docker build --no-cache -t mrak-os-prod .

echo "🔍 Verifying .env excluded..."
if docker run --rm mrak-os-prod ls -la /app/.env* 2>&1 | grep -q "No such file"; then
    echo "✅ .env excluded"
else
    echo "❌ .env found in image! SECURITY RISK!"
    exit 1
fi

echo "🔍 Verifying tests excluded..."
if docker run --rm mrak-os-prod ls /app/tests 2>&1 | grep -q "No such file"; then
    echo "✅ Tests excluded"
else
    echo "❌ Tests found in image!"
    exit 1
fi

echo "🔍 Running pip check for dependency conflicts..."
if ! docker run --rm mrak-os-prod pip check 2>&1; then
    echo "❌ pip check failed – dependency conflict!"
    exit 1
fi
echo "✅ pip check passed"

# Проверка импорта (пропускаем ошибки конфигурации)
echo "🔍 Verifying imports (allowing config errors)..."
IMPORT_OUTPUT=$(docker run --rm mrak-os-prod python -c "import server" 2>&1 || true)
if echo "$IMPORT_OUTPUT" | grep -q "ModuleNotFoundError"; then
    echo "❌ Failed to import server – missing modules!"
    echo "$IMPORT_OUTPUT"
    exit 1
elif echo "$IMPORT_OUTPUT" | grep -q "Traceback"; then
    echo "⚠️  Import succeeded but raised a configuration error (likely missing env vars)."
    echo "   This is expected in CI without secrets. Proceeding with health check."
else
    echo "✅ Server imports cleanly"
fi

# Запуск сервера с фиктивными переменными для проверки health
echo "🚀 Starting server container for health check..."
CONTAINER_ID=$(docker run -d -p 8000:8000 \
    -e DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy" \
    -e MASTER_KEY="dummykey12345678" \
    -e GROQ_API_KEY="dummy_groq_key" \
    mrak-os-prod)

# Ждём, пока контейнер начнёт слушать порт
echo "⏳ Waiting for server to start..."
for i in {1..10}; do
    if docker logs "$CONTAINER_ID" 2>&1 | grep -q "Uvicorn running on"; then
        echo "✅ Server is running"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Server did not start within timeout"
        docker logs "$CONTAINER_ID"
        docker rm -f "$CONTAINER_ID" >/dev/null
        exit 1
    fi
    sleep 2
done

# Дополнительная пауза для стабилизации
sleep 2

# Проверка health endpoint
echo "🔍 Testing /health endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || true)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed (HTTP $HTTP_CODE)"
    docker logs "$CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" >/dev/null
    exit 1
fi

# Останавливаем и удаляем контейнер
docker rm -f "$CONTAINER_ID" >/dev/null

echo "📏 Checking image size..."
SIZE=$(docker images mrak-os-prod --format "{{.Size}}" | sed 's/MB//')
if (( $(echo "$SIZE > 200" | bc -l) )); then
    echo "❌ Image too large: ${SIZE}MB (max 200MB)"
    exit 1
fi
echo "✅ Image size: ${SIZE}MB"

echo "✅ All Docker checks passed!"
# Cleanup old images
docker images mrak-os-prod --format "{{.ID}}" | tail -n +4 | xargs -r docker rmi 2>/dev/null || true
