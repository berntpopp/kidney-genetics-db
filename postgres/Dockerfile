FROM postgres:17.11-alpine3.24@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24

# The upstream image predates Alpine's CVE-2026-85091 fix.
RUN apk add --upgrade --no-cache zlib=1.3.2-r1
