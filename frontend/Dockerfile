# Stage 1: Builder
FROM node:25-alpine@sha256:5209bcaca9836eb3448b650396213dbe9d9a34d31840c2ae1f206cb2986a8543 AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production app (env vars will be injected at runtime)
RUN npm run build

# Stage 2: Production
FROM nginx:1.29-alpine@sha256:f46cb72c7df02710e693e863a983ac42f6a9579058a59a35f1ae36c9958e4ce0 AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# SECURITY: Configure nginx for non-root operation
RUN rm -f /etc/nginx/conf.d/default.conf.template && \
    # Move PID file to /tmp (writable by nginx user)
    # Note: nginx.conf has multiple spaces, so use [[:space:]]* to match any whitespace
    sed -i 's|pid[[:space:]]*[^ ;]*nginx\.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
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
