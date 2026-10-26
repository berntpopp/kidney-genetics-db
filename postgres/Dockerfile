FROM postgres:17.11-alpine3.24@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24

# The upstream image predates Alpine's CVE-2026-85091 (zlib) and CVE-2026-107891 (musl) fixes.
# Minimum versions: Alpine keeps only the newest build, so exact pins break later rebuilds.
RUN apk add --upgrade --no-cache 'zlib>=1.3.2-r1' 'musl>=1.2.6-r3' 'musl-utils>=1.2.6-r3'
