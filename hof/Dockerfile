FROM python:3.12-slim
WORKDIR /app
COPY hof/server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt
COPY hof/server/ /app/server/
COPY hof/www/ /app/www/
ENV PYTHONUNBUFFERED=1 \
    HOF_DB_PATH=/app/data/hof.db
VOLUME ["/app/data"]
EXPOSE 80
WORKDIR /app/server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
