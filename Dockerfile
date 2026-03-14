# ==================== STAGE 1: Build Frontend ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install ALL dependencies (including dev) for build
COPY frontend/package*.json ./
RUN npm ci && npm cache clean --force

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ==================== STAGE 2: Python Runtime (Debian slim) ====================
FROM python:3.10-slim

# Install system dependencies (supervisor and build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies (now fastembed/onnxruntime will install smoothly)
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt && \
    rm -rf /root/.cache/pip

# Copy only production backend files (NO dev scripts)
COPY server.py db.py schemas.py validation.py ./
COPY routers/ ./routers/
COPY repositories/ ./repositories/
COPY services/ ./services/
COPY domain/ ./domain/
COPY use_cases/ ./use_cases/
COPY utils/ ./utils/
COPY telegram_bot/ ./telegram_bot/
# Worker for background job processing
COPY worker.py ./
# Additional backend modules
COPY prompt_service.py prompt_loader.py artifact_service.py session_service.py dependencies.py groq_client.py ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisord.conf

# Cleanup pycache
RUN find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find . -name "*.pyc" -delete 2>/dev/null || true

EXPOSE 8000

# Start supervisor to run both API and worker
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]