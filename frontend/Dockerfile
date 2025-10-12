# Stage 1: Builder
FROM node:20-alpine@sha256:1ab6fc5a31d515dc7b6b25f6acfda2001821f2c2400252b6cb61044bd9f9ad48 AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production app (env vars will be injected at runtime)
RUN npm run build

# Stage 2: Production
FROM nginx:1.26-alpine@sha256:1eadbb07820339e8bbfed18c771691970baee292ec4ab2558f1453d26153e22d AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# SECURITY: Configure nginx for non-root operation
RUN rm -f /etc/nginx/conf.d/default.conf.template && \
    # Move PID file to /tmp (writable by nginx user) - note: multiple spaces in original
    sed -i 's|pid.*\/var\/run\/nginx\.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
    # Remove user directive (conflicts with USER instruction)
    sed -i '/^user/d' /etc/nginx/nginx.conf && \
    # Set ownership of all required directories
    chown -R nginx:nginx /usr/share/nginx/html \
                         /var/cache/nginx \
                         /var/log/nginx \
                         /etc/nginx/conf.d && \
    # Create cache subdirectories
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx && \
    # Redirect logs to stdout/stderr (Docker best practice)
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

# Copy entrypoint script (will run at container startup as nginx user)
COPY docker-entrypoint.sh /docker-entrypoint.d/40-inject-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/40-inject-runtime-env.sh

# SECURITY: Switch to non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
