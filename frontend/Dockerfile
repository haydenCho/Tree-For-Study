# Production build. Outputs static assets into a shared volume that Caddy serves.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM alpine:3.20
COPY --from=build /app/dist /app/dist
# Publish the built assets to the Caddy-shared volume, then stay alive so the
# volume mount persists for the lifetime of the stack.
CMD ["sh", "-c", "mkdir -p /dist && cp -a /app/dist/. /dist/ && echo 'frontend assets published to /dist' && tail -f /dev/null"]
