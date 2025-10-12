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
  API_BASE_URL: "${API_BASE_URL:-/api}",
  WS_URL: "${WS_URL:-/ws}",
  ENVIRONMENT: "${ENVIRONMENT:-production}",
  VERSION: "${VERSION:-0.2.0}"
};
EOF

echo "Runtime config generated:"
cat /usr/share/nginx/html/env-config.js

# Make sure index.html loads this script
# Add script tag to index.html if not already present
if ! grep -qi "env-config\.js" /usr/share/nginx/html/index.html; then
    # Use more robust sed pattern:
    # - 0,/pattern/ limits replacement to first match only
    # - [[:space:]]* matches any whitespace before closing tag
    # - Case-insensitive match for </head> or </HEAD>
    sed -i '0,/<\/[Hh][Ee][Aa][Dd]>/s|[[:space:]]*<\/\([Hh][Ee][Aa][Dd]\)>|  <script src="/env-config.js"></script>\n  </\1>|' /usr/share/nginx/html/index.html
    echo "Added env-config.js script tag to index.html"
fi

echo "Runtime environment injection complete"
