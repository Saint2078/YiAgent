FROM python:3.12-slim
WORKDIR /app
COPY factory/server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/
RUN pip install --no-cache-dir -e /app
COPY factory/server/ /app/server/
COPY factory/fixtures/ /app/fixtures/
COPY factory/www/ /app/www/
ENV PYTHONPATH=/app/src
EXPOSE 80
WORKDIR /app/server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
