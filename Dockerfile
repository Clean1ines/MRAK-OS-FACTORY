# ==================== STAGE 1: Build Frontend ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install ALL dependencies (including dev) for build
COPY frontend/package*.json ./
RUN npm ci && npm cache clean --force

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ==================== STAGE 2: Minimal Python Runtime ====================
FROM python:3.10-alpine

# Install system dependencies
RUN apk add --no-cache libffi openssl ca-certificates && \
    update-ca-certificates

WORKDIR /app

# Python dependencies
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
COPY generators/ ./generators/
COPY use_cases/ ./use_cases/
COPY utils/ ./utils/
# #ADDED: groq_client.py (was missing, causing import error)
COPY prompt_service.py prompt_loader.py artifact_service.py session_service.py workflow_engine.py logic.py groq_client.py ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Cleanup pycache
RUN find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find . -name "*.pyc" -delete 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
