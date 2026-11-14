FROM postgres:17.11-alpine3.24@sha256:3540c0362c809df084ffac0ae69fe794515f9de92692f02178bcdce0ef0302ac

# The upstream image predates Alpine's CVE-2026-85091 (zlib) and CVE-2026-107891 (musl) fixes.
# Minimum versions: Alpine keeps only the newest build, so exact pins break later rebuilds.
RUN apk add --upgrade --no-cache 'zlib>=1.3.2-r1' 'musl>=1.2.6-r3' 'musl-utils>=1.2.6-r3'
