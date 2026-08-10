# 鍘熷瀷闈欐€佺珯 路 nginx
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js factory-bench.js evolve-bench.js \
     optimize-bench.js agent-run-bench.js tour-bench.js role-factory.js rf-live.js \
     codebench-board.js \
     kb-specs.js kb-manage.js kb-packs-product.js dna-graph.html genome-packs.js \
     evolve-demo-pack.json evolve-seed-ai-kepu.json \
     factory-demo-snap.json factory-demo-snap-product-kb.json \
     role-factory-demo.json \
     benchmark-runnable-pack.json gene-case-links.js \
     /usr/share/nginx/html/
COPY vendor/force-graph.min.js /usr/share/nginx/html/vendor/force-graph.min.js

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD wget -q -O - http://127.0.0.1:8080/healthz || exit 1
