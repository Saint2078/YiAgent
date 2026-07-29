# Docker 部署说明

```bash
cd 20260726_Agent组装测试工厂Demo
docker compose up --build
```

打开 http://localhost:8787

- 镜像：`python:3.12-slim` + `python -m http.server` 托管 `www/`
- 仅静态 SPA + fixtures JSON，**不**调用大模型 API
- 口播稿：`docs/demo-script.md`
