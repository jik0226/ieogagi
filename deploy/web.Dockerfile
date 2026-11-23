# Web image: builds the React SPA and serves it with Caddy (automatic HTTPS),
# proxying /api to the backend on the internal network.
FROM node:26-alpine AS build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/frontend/dist /srv/www
