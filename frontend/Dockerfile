FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts

FROM base AS dev
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM base AS builder
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
RUN npm run build

FROM nginx:1.27-alpine
RUN apk upgrade --no-cache \
    && sed -i 's|^[[:space:]]*pid[[:space:]].*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf
COPY --from=builder --chmod=0555 /app/dist /usr/share/nginx/html
COPY --chmod=0444 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=0555 docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && ln -sf /tmp/env.js /usr/share/nginx/html/env.js \
    && chown -R nginx:nginx /etc/nginx/conf.d /usr/share/nginx/html /var/cache/nginx /var/log/nginx /var/run

EXPOSE 8080
USER 101
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
