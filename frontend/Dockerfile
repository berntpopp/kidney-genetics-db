# Stage 1: Builder
FROM node:26-alpine@sha256:e71ac5e964b9201072425d59d2e876359efa25dc96bb1768cb73295728d6e4ea AS builder

# SECURITY: Patch Alpine OS packages (busybox, musl, libssl/libcrypto, etc.)
RUN apk upgrade --no-cache

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production app (env vars will be injected at runtime)
RUN npm run build

# Stage 2: Production
FROM nginx:1.31-alpine@sha256:8b1e78743a03dbb2c95171cc58639fef29abc8816598e27fb910ed2e621e589a AS production

# SECURITY: Patch Alpine OS packages in the shipped image (busybox, musl,
# libssl3/libcrypto3, ssl_client, libcurl, zlib, etc.) — clears the Trivy
# code-scanning alerts on the frontend image.
RUN apk upgrade --no-cache

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
# Use 127.0.0.1 (not "localhost"): nginx binds IPv4 only (`listen 8080;`), but
# the container's "localhost" resolves to IPv6 ::1 first, so wget gets
# "connection refused" and the container is falsely marked unhealthy even while
# serving traffic. 127.0.0.1 forces the IPv4 stack nginx actually listens on.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/health || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
