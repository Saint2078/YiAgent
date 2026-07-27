# Optional API surface

本 Demo 由 nginx 直接托管静态资源与 `/fixtures/*.json`，无需独立 API 进程。

若后续接 live judge，可在此目录加 FastAPI，并由 compose 增加 `api` 服务；客户向电影回放路径保持零外网。
