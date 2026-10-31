"""Upstream inputs for position statistics (gnomAD, UniProt, AlphaFold DB) and the orchestrator.

Upstream payloads are cached 30 days (CacheService); the final result per gene, min_stars and
annotation timestamps. The statistics run in a worker thread, never on the event loop.
"""

import asyncio
import os
import re
from typing import Any

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.cache_service import get_cache_service
from app.core.exceptions import GeneNotFoundError
from app.core.logging import get_logger
from app.core.retry_utils import RetryableHTTPClient, RetryConfig
from app.core.version import get_package_version
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.services.position_stats import (
    STATS_VERSION,
    compute_position_statistics,
    refseq_needed,
)

logger = get_logger(__name__)

TTL = 30 * 24 * 3600
GNOMAD_URL = "https://gnomad.broadinstitute.org/api"
# Gene-level variants carry the most severe consequence across ALL transcripts (PAX2: 5 of
# them), so HGVSp positions mix isoforms. Take the variants of one transcript: MANE Select.
GNOMAD_GENE_QUERY = (
    "query($g:String!){ gene(gene_symbol:$g, reference_genome:GRCh38){ "
    "canonical_transcript_id mane_select_transcript{ ensembl_id refseq_id refseq_version } } }"
)
GNOMAD_QUERY = (
    "query($t:String!){ transcript(transcript_id:$t, reference_genome:GRCh38){ variants(dataset: "
    "gnomad_r4){ variant_id consequence hgvsp exome{ ac filters } genome{ ac filters } } } }"
)
GNOMAD_RELEASE = "gnomAD v4.1 (gnomad_r4)"
AF_FILES = "https://alphafold.ebi.ac.uk/files/"
MAX_CIF_BYTES = 50 * 1024 * 1024
_TOKEN = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")


class UpstreamError(Exception):
    """An upstream source failed; the message names the source (shown to the user, HTTP 502)."""


def _client() -> RetryableHTTPClient:
    ua = f"kidney-genetics-db/{get_package_version()} (+https://kidney-genetics.org)"
    return RetryableHTTPClient(
        httpx.AsyncClient(timeout=20.0, headers={"User-Agent": ua}, follow_redirects=True),
        RetryConfig(max_retries=2, max_delay=5.0),
    )


async def _request(source: str, send: Any, url: str, **kwargs: Any) -> httpx.Response:
    try:
        response: httpx.Response = await send(url, **kwargs)
        return response
    except httpx.HTTPStatusError as e:
        raise UpstreamError(f"{source} responded {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise UpstreamError(f"{source} request failed ({type(e).__name__})") from e


async def _gnomad(client: RetryableHTTPClient, query: str, variables: dict[str, str]) -> Any:
    res = await _request("gnomAD", client.post, GNOMAD_URL,
                         json={"query": query, "variables": variables})  # fmt: skip
    try:
        body = res.json()
    except ValueError as e:
        raise UpstreamError("gnomAD returned an unreadable response") from e
    if not isinstance(body, dict):
        raise UpstreamError("gnomAD returned an unreadable response")
    # Partial data would silently give the statistics an incomplete control set.
    if body.get("errors"):
        raise UpstreamError(f"gnomAD returned an error: {body['errors'][0].get('message')}")
    return body.get("data") or {}


async def fetch_gnomad_missense(client: RetryableHTTPClient, symbol: str) -> list[dict[str, Any]]:
    """Missense variants of the gene's MANE Select (else canonical) transcript.

    Each variant carries the MANE RefSeq transcript as "tx" (its protein is the exact sequence
    gnomAD's HGVSp numbering follows, when it matches no UniProt isoform).
    """
    gene = (await _gnomad(client, GNOMAD_GENE_QUERY, {"g": symbol})).get("gene")
    if not gene:
        raise UpstreamError(f"gnomAD has no data for {symbol}")
    mane = gene.get("mane_select_transcript") or {}
    tx = mane.get("ensembl_id") or gene.get("canonical_transcript_id")
    nm = (
        f"{mane['refseq_id']}.{mane['refseq_version']}"
        if mane.get("refseq_id") and mane.get("refseq_version")
        else None
    )
    if not tx:
        raise UpstreamError(f"gnomAD has no MANE or canonical transcript for {symbol}")
    transcript = (await _gnomad(client, GNOMAD_QUERY, {"t": tx})).get("transcript")
    if not transcript:
        raise UpstreamError(f"gnomAD has no data for transcript {tx}")
    variants = transcript.get("variants") or []
    return [
        {**v, "tx": nm} if nm else v for v in variants if v.get("consequence") == "missense_variant"
    ]


EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_CDS_HEAD = re.compile(r"^lcl\|(N[MR]_\d+\.\d+)_prot_")
_FASTA_RECORD = re.compile(r"^>", re.M)  # headers may contain ">" (HSD3B2: "5-->4-isomerase")
MAX_REFSEQ = 10  # transcripts fetched per gene; the rest stay unplaced (counted as mismatches)


async def fetch_refseq_proteins(client: RetryableHTTPClient, txs: list[str]) -> dict[str, str]:
    """Protein translation of each versioned RefSeq transcript (NM_138711.6 -> its NP sequence)."""
    params = {"db": "nuccore", "id": ",".join(txs), "rettype": "fasta_cds_aa", "retmode": "text"}
    if key := os.environ.get("NCBI_API_KEY"):
        params["api_key"] = key
    res = await _request("NCBI", client.get, EFETCH, params=params)
    out: dict[str, str] = {}
    for block in _FASTA_RECORD.split(res.text)[1:]:
        head, *lines = block.splitlines()
        m = _CDS_HEAD.match(head)
        if m and m[1] not in out:  # first CDS only
            out[m[1]] = "".join(line.strip() for line in lines)
    return out


def parse_fasta(text: str) -> dict[str, str]:
    """UniProt FASTA -> {accession or isoform id (Q02962-3): sequence}."""
    out: dict[str, str] = {}
    for block in _FASTA_RECORD.split(text)[1:]:
        head, *lines = block.splitlines()
        parts = head.split("|")
        if len(parts) >= 2:
            out[parts[1]] = "".join(line.strip() for line in lines)
    return out


async def fetch_uniprot_sequences(client: RetryableHTTPClient, accession: str) -> dict[str, str]:
    """Canonical sequence (key: the accession) plus every isoform, in one request."""
    res = await _request("UniProt", client.get,
                         "https://rest.uniprot.org/uniprotkb/stream",
                         params={"query": f"accession:{accession}", "format": "fasta",
                                 "includeIsoform": "true"})  # fmt: skip
    seqs = parse_fasta(res.text)
    if not seqs.get(accession):
        raise UpstreamError(f"UniProt returned no sequence for {accession}")
    return seqs


def parse_ca_atoms(cif: str) -> list[dict[str, Any]]:
    """C-alpha atoms from an mmCIF atom_site loop: resno, x, y, z and pLDDT (B_iso_or_equiv)."""
    cols: list[str] = []
    out: list[dict[str, Any]] = []
    in_loop = False
    for line in cif.splitlines():
        if line.startswith("_atom_site."):
            cols.append(line.split()[0][len("_atom_site.") :])
            in_loop = True
            continue
        if not in_loop or not cols:
            continue
        if not line.startswith(("ATOM", "HETATM")):
            if line.startswith(("loop_", "#", "_")):
                break
            continue
        row = dict(zip(cols, _TOKEN.findall(line), strict=False))
        if row.get("group_PDB") == "ATOM" and row.get("label_atom_id") == "CA":
            out.append({"resno": int(row["label_seq_id"]), "x": float(row["Cartn_x"]),
                        "y": float(row["Cartn_y"]), "z": float(row["Cartn_z"]),
                        "plddt": float(row["B_iso_or_equiv"])})  # fmt: skip
    return out


async def fetch_alphafold_model(
    client: RetryableHTTPClient, accession: str, length: int
) -> dict[str, Any]:
    """Canonical model (own accession, prefer F1); C-alpha residues only for a full-length model.
    {} = no prediction (a cacheable value, unlike None)."""
    try:
        res = await client.get(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (400, 404):  # no prediction
            return {}
        raise
    entries = res.json()
    own = [
        e for e in (entries if isinstance(entries, list) else [])
        if isinstance(e, dict) and e.get("uniprotAccession") == accession
        and isinstance(e.get("cifUrl"), str)
    ]  # fmt: skip
    entry = next((e for e in own if str(e.get("entryId", "")).endswith("-F1")), None) or (
        own[0] if own else None
    )
    if entry is None:
        return {}
    model = {"entryId": entry["entryId"], "version": entry.get("latestVersion"), "residues": None}
    # Never mix fragments: 3D statistics only on a model covering the whole protein.
    if entry.get("uniprotStart") == 1 and entry.get("uniprotEnd") == length:
        cif = await _download_cif(client, entry["cifUrl"])
        if cif is None:
            return {}
        model["residues"] = parse_ca_atoms(cif)
    return model


async def _download_cif(client: RetryableHTTPClient, url: str) -> str | None:
    """The model file, only from AlphaFold DB's file host, no redirects, at most 50 MB."""
    if not url.startswith(AF_FILES):
        logger.sync_warning("Ignoring AlphaFold cifUrl outside the file host", url=url)
        return None
    body = bytearray()
    async with client.client.stream("GET", url, follow_redirects=False) as res:
        res.raise_for_status()
        async for chunk in res.aiter_bytes():
            body += chunk
            if len(body) > MAX_CIF_BYTES:
                logger.sync_warning("AlphaFold model file over the size cap", url=url)
                return None
    return body.decode()


async def _cached(namespace: str, key: str, load: Any) -> Any:
    cache = get_cache_service()
    hit = await cache.get(key, namespace=namespace)
    if hit is not None:
        return hit
    value = await load()
    await cache.set(key, value, namespace=namespace, ttl=TTL)
    return value


def _annotation(db: Session, gene_id: Any, source: str) -> GeneAnnotation | None:
    return (
        db.query(GeneAnnotation)
        .filter(GeneAnnotation.gene_id == gene_id, GeneAnnotation.source == source)
        .order_by(GeneAnnotation.updated_at.desc())
        .first()
    )


def _load_gene(db: Session, symbol: str) -> dict[str, Any]:
    gene = db.query(Gene).filter(func.upper(Gene.approved_symbol) == symbol.upper()).first()
    if not gene:
        raise GeneNotFoundError(symbol)
    clinvar = _annotation(db, gene.id, "clinvar")
    uniprot = _annotation(db, gene.id, "uniprot")
    return {
        "symbol": gene.approved_symbol,
        "clinvar": (clinvar.annotations or {}) if clinvar else {},
        "clinvar_at": clinvar.updated_at.isoformat() if clinvar and clinvar.updated_at else None,
        "uniprot": (uniprot.annotations or {}) if uniprot else {},
        "uniprot_at": uniprot.updated_at.isoformat() if uniprot and uniprot.updated_at else None,
    }


async def get_position_statistics(db: Session, symbol: str, min_stars: int) -> dict[str, Any]:
    """Position statistics for a gene; raises GeneNotFoundError, LookupError or UpstreamError."""
    g = await run_in_threadpool(_load_gene, db, symbol)
    accession = g["uniprot"].get("accession")
    if not accession:
        raise LookupError(f"No UniProt accession for {g['symbol']}")
    # UniProt timestamp too: a domain refresh changes the domain tests.
    key = f"v{STATS_VERSION}:{g['symbol']}:{min_stars}:{g['clinvar_at']}:{g['uniprot_at']}"
    cache = get_cache_service(db)
    hit = await cache.get(key, namespace="position_stats")
    if hit is not None:
        return dict(hit)

    client = _client()
    try:
        seqs = await _cached("uniprot_isoforms", f"{accession}:{g['uniprot_at']}",
                             lambda: fetch_uniprot_sequences(client, accession))  # fmt: skip
        sequence = seqs[accession]
        length = int(g["uniprot"].get("length") or len(sequence))
        gnomad: Any
        model: Any
        gnomad, model = await asyncio.gather(
            _cached("gnomad_mane_missense_v2", g["symbol"],
                    lambda: fetch_gnomad_missense(client, g["symbol"])),
            _cached("alphafold_ca", f"{accession}:{length}",
                    lambda: fetch_alphafold_model(client, accession, length)),
            return_exceptions=True,
        )  # fmt: skip
        if isinstance(gnomad, BaseException):
            raise gnomad
        isoforms = {k: v for k, v in seqs.items() if k != accession}
        clinvar_rows = g["clinvar"].get("missense_residues")
        needed = await run_in_threadpool(
            refseq_needed, sequence, clinvar_rows, isoforms, min_stars, gnomad
        )
        refseq: dict[str, str] = {}
        if needed:
            needed = sorted(needed)[:MAX_REFSEQ]
            try:  # versioned accessions never change: cache as long as the rest
                refseq = await _cached("refseq_protein", ",".join(needed),
                                       lambda: fetch_refseq_proteins(client, needed))  # fmt: skip
            except UpstreamError as e:  # without them those variants stay unplaced
                logger.sync_warning("RefSeq proteins unavailable", gene=g["symbol"], error=str(e))
    finally:
        await client.close()

    # Linear statistics need only gnomAD/UniProt; an AlphaFold failure only drops 3D.
    spatial_error = None
    if isinstance(model, httpx.HTTPStatusError):
        spatial_error = f"AlphaFold responded {model.response.status_code}"
    elif isinstance(model, httpx.HTTPError):
        spatial_error = "AlphaFold did not respond"
    elif isinstance(model, Exception):  # unreadable reply or model file: still only 3D lost
        spatial_error = "AlphaFold returned an unreadable response"
    elif isinstance(model, BaseException):
        raise model
    if spatial_error:
        logger.sync_warning("AlphaFold unavailable for position statistics",
                            gene=g["symbol"], error=spatial_error)  # fmt: skip
        model = None

    result = await run_in_threadpool(
        lambda: compute_position_statistics(
            gene=g["symbol"],
            accession=accession,
            length=length,
            sequence=sequence,
            clinvar_residues=g["clinvar"].get("missense_residues"),
            gnomad=gnomad,
            domains=g["uniprot"].get("domains"),
            model=model,
            min_stars=min_stars,
            provenance={"clinvar": g["clinvar_at"], "gnomad": GNOMAD_RELEASE, "uniprot": accession},
            spatial_error=spatial_error,
            isoforms=isoforms,
            refseq=refseq,
        )
    )
    if not spatial_error:  # a transient AlphaFold outage must not stick for 30 days
        await cache.set(key, result, namespace="position_stats", ttl=TTL)
    logger.sync_info("Computed position statistics", gene=g["symbol"], status=result["status"])
    return result
