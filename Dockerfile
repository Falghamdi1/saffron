# One image serves both the API and the built web client.
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 AUTH_MODE=supabase
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY backend/data ./data
COPY supabase /app/supabase
COPY --from=web /web/dist /app/frontend/dist
RUN useradd --system saffron
USER saffron
# Applying the schema is idempotent, so every deploy also refreshes the menu.
CMD ["sh", "-c", "python -m app.setup_db && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
