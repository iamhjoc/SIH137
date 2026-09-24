# Multi-stage build: compile the Vite app, then serve the static output
# with a minimal nginx image. Build-time env vars (VITE_*) must be passed
# as --build-arg since Vite inlines them at build time, not runtime:
#
#   docker build \
#     --build-arg VITE_API_BASE=https://api.yourdomain.com/api/v1 \
#     --build-arg VITE_MAP_TILE_URL=... \
#     -t sih26137-frontend .

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE
ARG VITE_MAP_TILE_URL
ARG VITE_MAP_TILE_KEY
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_MAP_TILE_URL=$VITE_MAP_TILE_URL
ENV VITE_MAP_TILE_KEY=$VITE_MAP_TILE_KEY

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
