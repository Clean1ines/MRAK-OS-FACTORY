FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "httpx==0.27.2" "groq==0.4.2" requests
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
# Запуск через скрипт, чтобы поднять и пингер, и streamlit
ENTRYPOINT ["sh", "-c", "python3 keep_alive.py & streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]