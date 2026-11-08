# Debian Node for the build stage: node:20-alpine has segfaulted on
# `npm ci` under Podman machine (applehv) on this host.
FROM node:20-bookworm-slim AS build

WORKDIR /app
COPY web-client/package.json web-client/package-lock.json ./
RUN npm ci
COPY web-client/ ./
# Browser talks to same origin; nginx proxies /api and /ws
ENV VITE_API_BASE=/api
RUN npm run build

FROM nginx:1.27-alpine
COPY deployment/docker/web-client/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
