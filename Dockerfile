# Build the static operator dashboard with its API origin left relative.
FROM node:20-alpine AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

# Serve the static dashboard and deterministic FastAPI surface from one public
# Container App. No database, credential, or third-party callback is required.
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INTERLOCK_STATIC_DIR=/app/web/out
WORKDIR /app
COPY pyproject.toml ./
COPY interlock/ ./interlock/
RUN pip install --no-cache-dir .
COPY --from=web-build /build/web/out /app/web/out
RUN mkdir -p /tmp/interlock
EXPOSE 8000
CMD ["uvicorn", "interlock.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
