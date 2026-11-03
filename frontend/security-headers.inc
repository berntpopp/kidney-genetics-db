# Security headers for every response. nginx drops ALL inherited add_header directives in a
# location that sets its own, so include this file at server level AND in every such location.
# No HSTS here: the TLS edge proxy sends it on every response; a second value would conflict.
# $csp is mapped per route in nginx.prod.conf (Swagger/ReDoc need a relaxed policy).
add_header Content-Security-Policy $csp always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()" always;

# nginx is the single source of these headers; drop the backend's copies so proxied
# responses never carry two conflicting values (e.g. X-Frame-Options DENY + SAMEORIGIN).
proxy_hide_header Content-Security-Policy;
proxy_hide_header X-Frame-Options;
proxy_hide_header X-Content-Type-Options;
proxy_hide_header Referrer-Policy;
proxy_hide_header Permissions-Policy;
