#!/bin/sh
# Runtime environment variable injection for Vue.js
# This solves the "build once, deploy anywhere" problem with Vite

set -e

echo "Injecting runtime environment variables..."

# Generate runtime config accessible to Vue.js app
cat > /usr/share/nginx/html/env-config.js <<EOF
// Runtime environment configuration
// Injected at container startup
window._env_ = {
  API_BASE_URL: "${API_BASE_URL:-}",
  WS_URL: "${WS_URL:-/ws}",
  MCP_BASE_URL: "${MCP_BASE_URL:-}",
  ENVIRONMENT: "${ENVIRONMENT:-production}",
  VERSION: "${VERSION:-0.2.0}"
};
EOF

echo "Runtime config generated:"
cat /usr/share/nginx/html/env-config.js

# Make sure every prerendered page loads this script.
# vite-ssg emits one index.html per route (index.html, mcp/index.html, ...),
# so the tag must be injected into all of them — not just the root — or
# window._env_ is undefined on prerendered subpages.
find /usr/share/nginx/html -name 'index.html' -type f | while read -r html; do
    if ! grep -q "env-config.js" "$html"; then
        sed -i 's|</head>|  <script src="/env-config.js"></script>\n  </head>|' "$html"
    fi
done
echo "Added env-config.js script tag to all prerendered pages"

echo "Runtime environment injection complete"
