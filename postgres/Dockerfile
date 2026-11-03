FROM postgres:17.11-alpine3.24@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b

# The upstream image predates Alpine's CVE-2026-85091 (zlib) and CVE-2026-107891 (musl) fixes.
# Minimum versions: Alpine keeps only the newest build, so exact pins break later rebuilds.
RUN apk add --upgrade --no-cache 'zlib>=1.3.2-r1' 'musl>=1.2.6-r3' 'musl-utils>=1.2.6-r3'
