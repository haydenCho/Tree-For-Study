# 운영 빌드. 정적 산출물을 Caddy가 서빙하는 공유 볼륨으로 내보낸다.
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
# 빌드 산출물을 Caddy 공유 볼륨(/dist)에 복사한 뒤, 스택이 떠 있는 동안
# 볼륨 마운트가 유지되도록 컨테이너를 살려 둔다.
CMD ["sh", "-c", "mkdir -p /dist && cp -a /app/dist/. /dist/ && echo 'frontend assets published to /dist' && tail -f /dev/null"]
