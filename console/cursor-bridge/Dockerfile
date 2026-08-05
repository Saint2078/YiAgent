# Agent bridge · Linux 内装依赖（含 sqlite3）· DEC-044
FROM node:20-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 make g++ \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev

COPY server.mjs ./

ENV HOST=0.0.0.0
ENV PORT=8091
ENV WORKBENCH_CWD=/workbench

EXPOSE 8091
CMD ["node", "server.mjs"]
