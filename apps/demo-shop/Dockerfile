# syntax=docker/dockerfile:1.7
# glibc-based image: required by the OTel Operator's Python auto-instrumentation.
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ARG VERSION=dev
LABEL org.opencontainers.image.title="demo-shop" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/CHANGE_ME/observability-lab"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=${VERSION}
COPY --from=build /install /usr/local
WORKDIR /srv
COPY app/ app/
RUN useradd --uid 10001 --no-create-home shop
USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
