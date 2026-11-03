#!/usr/bin/env bash
# Smoke test for the frontend nginx image: every response must carry the security headers,
# whatever its status (a 404 is fine) and whichever location served it.
# Usage: scripts/check-security-headers.sh http://127.0.0.1:8080
set -euo pipefail

base="${1:?usage: $0 BASE_URL}"
required=(content-security-policy x-frame-options x-content-type-options referrer-policy permissions-policy)
fail=0

# A real hashed asset from the built page
asset=$(curl -fsS "$base/" | grep -o '/assets/[^"]*\.js' | head -n 1)
[ -n "$asset" ] || { echo "FAIL: no /assets/*.js referenced from /"; exit 1; }

check() { # path, exact Cache-Control count (or "any")
  local path="$1" want_cc="$2" headers status
  headers=$(curl -sS -o /dev/null -D - "$base$path" | tr -d '\r' | tr 'A-Z' 'a-z')
  status=$(head -n 1 <<<"$headers" | cut -d' ' -f2)
  for h in "${required[@]}"; do
    if ! grep -q "^$h:" <<<"$headers"; then echo "FAIL $path ($status): missing $h"; fail=1; fi
    if [ "$(grep -c "^$h:" <<<"$headers")" -gt 1 ]; then echo "FAIL $path ($status): duplicate $h"; fail=1; fi
  done
  grep -q '^x-content-type-options: nosniff$' <<<"$headers" || { echo "FAIL $path: nosniff"; fail=1; }
  if [ "$want_cc" != any ] && [ "$(grep -c '^cache-control:' <<<"$headers")" -ne "$want_cc" ]; then
    echo "FAIL $path ($status): expected $want_cc Cache-Control header(s)"; fail=1
  fi
  echo "checked $path ($status)"
}

check / 1
check /about 1
check "$asset" 1
check /env-config.js 1
check /videos/videos.json 1
check /health any
# Backend-proxied docs (502 without a backend is fine): relaxed CSP plus the frame headers
check /docs any
curl -sS -o /dev/null -D - "$base/docs" | grep -qi '^content-security-policy:.*cdn.jsdelivr.net' \
  || { echo "FAIL /docs: relaxed docs CSP missing"; fail=1; }

[ "$fail" -eq 0 ] && echo "All security header checks passed"
exit "$fail"
