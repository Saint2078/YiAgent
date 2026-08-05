# 原型静态站 · nginx
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js factory-bench.js evolve-bench.js \
     kb-specs.js kb-manage.js dna-graph.html \
     evolve-demo-pack.json evolve-seed-ai-kepu.json \
     /usr/share/nginx/html/
COPY vendor/force-graph.min.js /usr/share/nginx/html/vendor/force-graph.min.js

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD wget -q -O - http://127.0.0.1:8080/healthz || exit 1
