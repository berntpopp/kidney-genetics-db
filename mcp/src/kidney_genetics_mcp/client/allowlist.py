"""Code-enforced allowlist of read-only, side-effect-free KGDB ``/api`` paths.

SECURITY BOUNDARY — the runtime regex enforcement and the hand-curated deny-list
below are deliberate and must not be auto-derived. Only ``GET`` is ever allowed;
every write/admin/auth/pipeline/staging surface is denied explicitly so a
contract test can prove there are no silent gaps whenever the backend adds a
route.
"""

from __future__ import annotations

import re

#: Allowed read-only path patterns. Only ``GET`` requests on these are permitted.
_ALLOW: list[re.Pattern[str]] = [
    re.compile(r"^/api/genes/resolve$"),
    re.compile(r"^/api/genes/?$"),
    re.compile(r"^/api/genes/[^/]+/evidence$"),
    re.compile(r"^/api/genes/[^/]+$"),
    re.compile(r"^/api/annotations/genes/\d+/annotations$"),
    re.compile(r"^/api/annotations/genes/\d+/annotations/summary$"),
    re.compile(r"^/api/annotations/sources$"),
    re.compile(r"^/api/statistics/summary$"),
    re.compile(r"^/api/datasources/?$"),
    re.compile(r"^/api/releases/?$"),
]

#: Explicit deny guards (defense-in-depth; these also fail the catch-all below).
#: Every privileged / side-effecting surface is denied by name so the contract
#: test can confirm no silent gaps.
_DENY: list[re.Pattern[str]] = [
    re.compile(p)
    for p in (
        r"^/api/admin",
        r"^/api/auth",
        r"^/api/staging",
        r"^/api/ingestion",
        r"^/api/progress",
        r"^/api/network",
    )
]

#: The allowlist patterns, exposed for the contract / security tests.
ALLOWED: list[str] = [r.pattern for r in _ALLOW]
DENIED: list[str] = [r.pattern for r in _DENY]


def is_denied(path: str) -> bool:
    """Return True if *path* matches an explicit deny rule.

    Args:
        path: The API path to test.

    Returns:
        ``True`` when an explicit deny pattern matches.
    """
    return any(d.search(path) for d in _DENY)


def is_allowed(method: str, path: str) -> bool:
    """Return True if a ``GET`` on *path* is on the allowlist and not denied.

    Args:
        method: The HTTP method (only ``GET`` is ever allowed).
        path: The API path relative to the host.

    Returns:
        ``True`` only when *method* is ``GET``, *path* is not explicitly denied,
        and *path* matches an allow pattern.
    """
    if method.upper() != "GET":
        return False
    if is_denied(path):
        return False
    return any(rule.match(path) for rule in _ALLOW)


def assert_allowed(method: str, path: str) -> None:
    """Raise :class:`PermissionError` unless a ``GET`` on *path* is allowlisted.

    This is the enforced security boundary called before any HTTP request.

    Args:
        method: The HTTP method (only ``GET`` is permitted).
        path: The API path relative to the host.

    Raises:
        PermissionError: If the method is not ``GET`` or the path is not on the
            allowlist (or is explicitly denied).
    """
    if not is_allowed(method, path):
        raise PermissionError(f"method/path not allowlisted: {method} {path}")
