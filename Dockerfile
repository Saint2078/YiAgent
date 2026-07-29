# YiAgent entity — Hermes-style: immutable install + durable home volume
FROM python:3.12-slim

WORKDIR /opt/yiagent

COPY pyproject.toml setup.py README.md /opt/yiagent/
COPY src/ /opt/yiagent/src/
COPY docker/entrypoint.sh /opt/yiagent/docker/entrypoint.sh

RUN pip install --no-cache-dir -e /opt/yiagent \
  && chmod +x /opt/yiagent/docker/entrypoint.sh \
  && mkdir -p /opt/data

ENV PYTHONUNBUFFERED=1
ENV YIAGENT_HOME=/opt/data
ENV YIAGENT_CWD=/opt/data/workspace

VOLUME ["/opt/data"]
WORKDIR /opt/data/workspace

ENTRYPOINT ["/opt/yiagent/docker/entrypoint.sh"]
CMD ["chat"]
