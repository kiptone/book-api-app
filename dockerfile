FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ ./src/

# Переменные окружения по умолчанию
ARG EVENTS_PROVIDER_BASE_URL=http://events-provider.dev-2.python-labs.ru
ARG EVENTS_PROVIDER_API_KEY=EFyEe5G6vy1GLV8khDYwDSndSKYo0UMPYRZszM6Pxm0

ENV EVENTS_PROVIDER_BASE_URL=${EVENTS_PROVIDER_BASE_URL}
ENV EVENTS_PROVIDER_API_KEY=${EVENTS_PROVIDER_API_KEY}

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
