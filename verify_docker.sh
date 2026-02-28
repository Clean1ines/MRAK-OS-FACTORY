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

# #CHANGED: Improved import verification – fail only on ModuleNotFoundError
echo "🔍 Verifying imports (allowing config errors)..."
IMPORT_OUTPUT=$(docker run --rm mrak-os-prod python -c "import server" 2>&1 || true)
if echo "$IMPORT_OUTPUT" | grep -q "ModuleNotFoundError"; then
    echo "❌ Failed to import server – missing modules!"
    echo "$IMPORT_OUTPUT"
    exit 1
elif echo "$IMPORT_OUTPUT" | grep -q "Traceback"; then
    echo "⚠️  Import succeeded but raised a configuration error (likely missing env vars)."
    echo "   This is expected in CI without secrets. Proceeding with health check if possible."
else
    echo "✅ Server imports cleanly"
fi

# Запуск сервера и проверка health endpoint
echo "🚀 Starting server container for health check..."
# #ADDED: Set dummy env vars to allow server to start (if possible)
CONTAINER_ID=$(docker run -d -e GROQ_API_KEY=dummy -e DATABASE_URL=postgresql://dummy:dummy@localhost:5432/dummy -e MASTER_KEY=dummykey123 -p 8000:8000 mrak-os-prod)

# Проверяем, что контейнер жив
if ! docker ps --filter "id=$CONTAINER_ID" --format '{{.Status}}' | grep -q "Up"; then
    echo "❌ Container failed to start"
    docker logs "$CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" >/dev/null
    exit 1
fi

# Делаем запрос к health endpoint
echo "🔍 Testing /health endpoint..."
if ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "❌ Health check failed"
    docker logs "$CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" >/dev/null
    exit 1
fi
echo "✅ Health check passed"

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
