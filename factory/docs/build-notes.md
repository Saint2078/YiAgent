# Build the SPA before docker compose (inside container if preferred):
#   docker run --rm -v "$PWD/app:/src" -w /src node:22-bookworm-slim \
#     sh -c "npm install && npm run build"
# Or on a machine with Node: cd app && npm install && npm run build
#
# Then:
#   docker compose up --build
