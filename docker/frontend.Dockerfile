# React dashboard, built once and served as static files by nginx.
FROM node:24-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Empty means "same origin": the page then asks nginx for /api/..., which
# proxies to the backend, so one published port is enough and the demo also
# works from another machine on the network. Point this at an absolute URL
# (e.g. http://127.0.0.1:8000) to talk to a backend outside the compose stack.
ARG VITE_BACKEND_URL=
RUN printf 'VITE_BACKEND_URL=%s\n' "$VITE_BACKEND_URL" > .env.production.local \
    && npx vite build

FROM nginx:1.29-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
