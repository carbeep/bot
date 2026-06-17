FROM python:3.12-slim

WORKDIR /app

COPY bot/pyproject.toml bot/pyproject.toml
RUN pip install --no-cache-dir -e bot/

COPY bot/ bot/

CMD ["python", "-m", "bot"]
