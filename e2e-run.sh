#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

FE_PORT=5173; BE_PORT=8000

echo "🎭 [1/4] Cleaning ports..."
for port in $FE_PORT $BE_PORT; do
  command -v fuser >/dev/null 2>&1 && fuser -k ${port}/tcp 2>/dev/null || true
done
sleep 1

echo "🎭 [2/4] Starting backend..."
# Start test database first
echo "🎭 Starting test database..."
bash scripts/ensure_test_db.sh
export DATABASE_URL="postgresql://test:test123@localhost:5433/mrak_test"
python -m uvicorn server:app --host 127.0.0.1 --port $BE_PORT > /tmp/be.log 2>&1 &
BE_PID=$!
sleep 2

echo "🎭 [3/4] Starting frontend..."
npm run dev:frontend -- --port $FE_PORT --host 127.0.0.1 --open false > /tmp/fe.log 2>&1 &
FE_PID=$!

echo "🎭 [4/4] Waiting..."
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$BE_PORT" >/dev/null 2>&1 && break
  [ $i -eq 30 ] && { tail -5 /tmp/be.log; exit 1; }
  sleep 1
done
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$FE_PORT" >/dev/null 2>&1 && break
  [ $i -eq 30 ] && { tail -5 /tmp/fe.log; exit 1; }
  sleep 1
done
sleep 2

echo "🎭 Running tests..."
cd "$ROOT/frontend"
npx playwright test --config="$ROOT/playwright.config.ts" --reporter=list --timeout=20000 "${@}"
RESULT=$?

kill $BE_PID $FE_PID 2>/dev/null || true
exit $RESULT
