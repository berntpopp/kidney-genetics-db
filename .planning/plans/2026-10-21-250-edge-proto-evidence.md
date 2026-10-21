# #250 edge scheme: evidence checklist before merge

Branch `prep/250-edge-proto` (not in the v0.7.x PR). Merge only after every box is ticked with production evidence.

## What the branch changes
- `frontend/nginx.prod.conf`: all six proxy locations (sitemap, /api/, openapi.json, /docs, /redoc, progress WebSocket) forward `$edge_proto`: the edge's `X-Forwarded-Proto` when it is exactly `http`/`https` **and** the peer is in `geo $from_edge`; otherwise the local `$scheme`. Default trust list is `127.0.0.1` only, so behaviour is unchanged until the NPM address is filled in.
- nginx reaches the backend via the network-scoped alias `kgdb-backend-internal` (internal net only).
- `docker-compose.prod.yml`: internal net gets a fixed subnet (`KGDB_INTERNAL_SUBNET`, default 172.30.250.0/24); frontend gets a fixed IP (`KGDB_FRONTEND_IP`, default 172.30.250.10); backend `FORWARDED_ALLOW_IPS` = that IP (never `*`; the backend also sits on `npm_default`).

## Evidence needed (production host)
- [ ] NPM container address(es) on `npm_default` and whether they are fixed (berntpopp/strato_v6_docker_npm#28). `docker network inspect npm_default`.
- [ ] Every other container on `npm_default` listed (shared network is not exclusive); none of them is in the nginx `geo` list.
- [ ] 172.30.250.0/24 free on the host (`docker network ls -q | xargs docker network inspect -f '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}'`), else set `KGDB_INTERNAL_SUBNET`/`KGDB_FRONTEND_IP`.
- [ ] Fill NPM address into `geo $from_edge`; `nginx -t` in the frontend image.

## Deploy steps (when approved)
1. `docker compose -f docker-compose.prod.yml down` (the internal network must be recreated to get the subnet), then `up -d --build frontend backend`.
2. Verify, with backend request logging:
   - [ ] HTTPS via edge → backend `request.url` is `https://…`; HTTP via edge → `http://…`.
   - [ ] `curl -H 'X-Forwarded-Proto: https'` from another container on `npm_default` straight to the frontend → backend sees `http`.
   - [ ] Same forged header straight to the backend from `npm_default` → uvicorn ignores it (peer not in `FORWARDED_ALLOW_IPS`).
   - [ ] Invalid value (`X-Forwarded-Proto: gopher`) from the edge → local scheme.
   - [ ] Progress WebSocket connects via `wss://` through the edge.
