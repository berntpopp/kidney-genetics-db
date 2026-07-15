"""Anti-drift tests tying the code-enforced allowlist to the OpenAPI snapshot.

These guard the security boundary against backend drift (HNF1B idea): the
allowlist regexes in :mod:`kidney_genetics_mcp.client.allowlist` are checked
against the committed ``contract/openapi.snapshot.json`` so that

  (a) every ALLOW rule still corresponds to a real backend GET route (catch a
      stale rule whose route was removed/renamed), and
  (b) the GET routes the MCP actually consumes (spec §4 catalog) stay allowed,
      while every privileged surface (admin/auth/staging/ingestion/pipeline/...)
      stays denied — forcing an explicit allow/deny decision whenever the
      backend adds a route.

The MCP uses a narrow explicit allowlist + a small defense-in-depth deny-list,
with everything else default-denied by the catch-all in ``is_allowed``. So
"decided" here means: allowed (``is_allowed``) XOR effectively-denied
(``assert_allowed`` raises). Detail endpoints under an exposed domain that no
tool consumes are *effectively denied* and that is asserted explicitly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from kidney_genetics_mcp.client.allowlist import (
    ALLOWED,
    assert_allowed,
    is_allowed,
    is_denied,
)

# --------------------------------------------------------------------------- #
# Snapshot loading                                                            #
# --------------------------------------------------------------------------- #

_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1] / "contract" / "openapi.snapshot.json"
)

# Concrete sample values for templated snapshot paths. Match the allowlist
# regexes: bare-digit gene_id (``\d+``) and a symbol/version slug (``[^/]+``).
_PARAM_SAMPLES: dict[str, str] = {
    "gene_symbol": "PKD1",
    "gene_id": "123",
    "version": "2024.01",
    "release_id": "5",
    "source_name": "panelapp",
    "source": "panelapp",
    "user_id": "7",
    "setting_id": "1",
    "namespace": "annotations",
    "key": "k1",
    "backup_id": "b1",
    "job_id": "j1",
    "upload_id": "u1",
    "staging_id": "s1",
    "identifier": "id1",
}


def _substitute(template: str) -> str:
    """Replace ``{param}`` placeholders with concrete sample values."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return _PARAM_SAMPLES.get(name, "X")

    return re.sub(r"\{([^}]+)\}", repl, template)


def _load_snapshot() -> dict[str, dict[str, object]]:
    """Return the snapshot ``paths`` object (template -> {method: ...})."""
    with _SNAPSHOT_PATH.open(encoding="utf-8") as fh:
        spec = json.load(fh)
    paths = spec.get("paths")
    assert isinstance(paths, dict) and paths, "snapshot has no paths"
    return paths


_PATHS = _load_snapshot()

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _get_templates() -> list[str]:
    """Every snapshot path template that declares a GET method."""
    return sorted(
        template
        for template, ops in _PATHS.items()
        if any(m.lower() == "get" for m in ops if m.lower() in _HTTP_METHODS)
    )


# The exact GET routes the MCP consumes (spec §4 catalog). Each MUST stay
# allowed; if a backend rename breaks one, the allow assertion below fails.
_EXPOSED_CONSUMED_TEMPLATES: tuple[str, ...] = (
    "/api/genes/resolve",
    "/api/genes/",
    "/api/genes/{gene_symbol}",
    "/api/genes/{gene_symbol}/evidence",
    "/api/annotations/genes/{gene_id}/annotations",
    "/api/annotations/genes/{gene_id}/annotations/summary",
    "/api/annotations/sources",
    "/api/statistics/summary",
    "/api/datasources/",
    "/api/releases/",
)

# Exposed domains the spec scopes the MCP to. Used to find detail endpoints that
# fall inside an exposed domain but are NOT consumed by any tool — those must be
# effectively denied (no silent exposure).
_EXPOSED_DOMAINS: tuple[str, ...] = (
    "/api/genes",
    "/api/annotations/genes",
    "/api/annotations/sources",
    "/api/statistics/summary",
    "/api/datasources",
    "/api/releases",
)

# Prefixes that must always be denied (privileged / side-effecting surfaces).
_NON_EXPOSED_PREFIXES: tuple[str, ...] = (
    "/api/admin",
    "/api/auth",
    "/api/staging",
    "/api/ingestion",
    "/api/progress",
    "/api/network",
)


# --------------------------------------------------------------------------- #
# (a) every ALLOW rule maps to a real backend GET route                       #
# --------------------------------------------------------------------------- #


def test_every_allow_rule_matches_a_real_snapshot_get_path() -> None:
    """Each ALLOW regex must match >=1 non-denied GET path in the snapshot.

    Catches a stale allow rule whose backend route was removed or renamed.
    """
    probes = [_substitute(t) for t in _get_templates()]
    for pattern in ALLOWED:
        rule = re.compile(pattern)
        matched = [p for p in probes if rule.match(p) and not is_denied(p)]
        assert matched, (
            f"allow rule {pattern!r} matches no real (non-denied) GET path in "
            "the snapshot — the rule is stale or its backend route was "
            "removed/renamed"
        )


# --------------------------------------------------------------------------- #
# (b) the consumed exposed routes are allowed                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("template", _EXPOSED_CONSUMED_TEMPLATES)
def test_consumed_exposed_get_path_is_allowed(template: str) -> None:
    """Every GET route the MCP consumes must be present + allowed in the snapshot."""
    assert template in _PATHS, f"{template} missing from snapshot"
    assert any(m.lower() == "get" for m in _PATHS[template]), (
        f"{template} has no GET in snapshot"
    )
    path = _substitute(template)
    assert is_allowed("GET", path) is True, f"consumed GET {path} is not allowed"
    assert_allowed("GET", path)  # must not raise


def test_resolve_endpoint_present_and_allowed() -> None:
    """``/api/genes/resolve`` must be in the snapshot now and GET-allowlisted."""
    assert "/api/genes/resolve" in _PATHS, "resolve endpoint absent from snapshot"
    assert any(m.lower() == "get" for m in _PATHS["/api/genes/resolve"])
    assert is_allowed("GET", "/api/genes/resolve") is True


# --------------------------------------------------------------------------- #
# (c) coverage: every exposed-domain GET is decided (allowed XOR denied)       #
# --------------------------------------------------------------------------- #


def test_every_exposed_domain_get_is_decided() -> None:
    """No exposed-domain GET route is silently permitted.

    Each exposed-domain GET path is either explicitly allowed (consumed routes)
    or effectively denied (``assert_allowed`` raises) — never silently open.
    This forces an explicit allow/deny decision when the backend adds a route
    under an already-exposed domain.
    """
    undecided: list[str] = []
    for template in _get_templates():
        if not any(template.startswith(d) for d in _EXPOSED_DOMAINS):
            continue
        path = _substitute(template)
        allowed = is_allowed("GET", path)
        try:
            assert_allowed("GET", path)
            effectively_denied = False
        except PermissionError:
            effectively_denied = True
        # Decided == allowed XOR effectively-denied (assert_allowed mirrors
        # is_allowed, so the two are always opposite; this guards that invariant
        # and that nothing is both-or-neither).
        if allowed == effectively_denied:
            undecided.append(f"{template} (allowed={allowed})")
    assert not undecided, (
        "exposed-domain GET paths with an inconsistent allow/deny decision: "
        f"{undecided}"
    )


def test_exposed_detail_endpoints_not_consumed_are_denied() -> None:
    """Exposed-domain detail GETs no tool consumes must be effectively denied.

    These (e.g. ``/api/releases/{version}``, ``/api/datasources/{source_name}``)
    sit inside an exposed domain but are outside the §4 catalog, so they must NOT
    be reachable through the allowlist.
    """
    consumed = {_substitute(t) for t in _EXPOSED_CONSUMED_TEMPLATES}
    checked: list[str] = []
    for template in _get_templates():
        if not any(template.startswith(d) for d in _EXPOSED_DOMAINS):
            continue
        path = _substitute(template)
        if path in consumed:
            continue
        checked.append(template)
        assert is_allowed("GET", path) is False, (
            f"non-consumed exposed-domain GET {path} is unexpectedly allowed"
        )
        with pytest.raises(PermissionError):
            assert_allowed("GET", path)
    # Sanity: the snapshot really does contain such detail endpoints, so this
    # test is exercising something (guards against a vacuous pass).
    assert checked, "expected non-consumed exposed-domain detail GET paths"


# --------------------------------------------------------------------------- #
# (d) a representative sample of privileged routes must be denied              #
# --------------------------------------------------------------------------- #


def _non_exposed_get_templates() -> list[str]:
    return [
        t
        for t in _get_templates()
        if any(t.startswith(pre) for pre in _NON_EXPOSED_PREFIXES)
    ]


def test_non_exposed_privileged_get_paths_are_denied() -> None:
    """A real sample of admin/auth/staging/ingestion/progress/network GETs is denied."""
    templates = _non_exposed_get_templates()
    # Guard against a vacuous pass if the snapshot ever drops these surfaces.
    assert len(templates) >= 5, "expected privileged GET routes in the snapshot"
    for template in templates:
        path = _substitute(template)
        assert is_allowed("GET", path) is False, f"privileged GET {path} is allowed"
        with pytest.raises(PermissionError):
            assert_allowed("GET", path)
