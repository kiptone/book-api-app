FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ ./src/

# Переменные окружения по умолчанию
ENV EVENTS_PROVIDER_BASE_URL=https://events-provider.dev-2.python-labs.ru
ENV EVENTS_PROVIDER_API_KEY=EFyEe5G6vy1GLV8khDYwDSndSKYo0UMPYRZszM6Pxm0

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
