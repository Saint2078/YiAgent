FROM python:3.12-alpine
WORKDIR /app
COPY db.py server.py kb.py ./
COPY migrations ./migrations
ENV OPC_01_DB=/data/opc.sqlite
ENV PORT=8090
ENV KB_SEED_DIR=/workbench/kb-seed
ENV KB_DOCS_DIR=/workbench/kb
EXPOSE 8090
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --retries=6 --start-period=5s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz')"
CMD ["python3", "server.py"]
