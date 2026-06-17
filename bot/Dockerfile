FROM python:3.12-slim

WORKDIR /app/bot

COPY bot/pyproject.toml .
RUN pip install --no-cache-dir .

COPY bot/ .

CMD ["python", "__main__.py"]
