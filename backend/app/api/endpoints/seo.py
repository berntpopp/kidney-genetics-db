"""
SEO endpoints - sitemap.xml generation

Public access, no auth required.
"""

import time
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models.gene import Gene

router = APIRouter()
logger = get_logger(__name__)

# Module-level cache: (xml_bytes, timestamp)
_sitemap_cache: tuple[bytes, float] = (b"", 0.0)
_CACHE_TTL = 3600  # 1 hour


def _build_sitemap_xml(symbols: list[str]) -> bytes:
    """Build sitemap XML from a list of gene symbols."""
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    base = settings.SITE_URL.rstrip("/")

    # Static pages
    static_paths = [
        ("/", "1.0", "weekly"),
        ("/genes", "0.9", "daily"),
        ("/dashboard", "0.7", "weekly"),
        ("/data-sources", "0.7", "weekly"),
        ("/network-analysis", "0.7", "weekly"),
        ("/about", "0.5", "monthly"),
    ]
    for path, priority, changefreq in static_paths:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{base}{path}"
        SubElement(url_el, "priority").text = priority
        SubElement(url_el, "changefreq").text = changefreq

    # Dynamic gene pages
    for symbol in symbols:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{base}/genes/{symbol}"
        SubElement(url_el, "priority").text = "0.8"
        SubElement(url_el, "changefreq").text = "weekly"

    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(
        urlset, encoding="unicode"
    ).encode("utf-8")


def _query_gene_symbols(db: Session) -> list[str]:
    """Query all gene symbols from database."""
    stmt = select(Gene.approved_symbol).order_by(Gene.approved_symbol)
    return [row[0] for row in db.execute(stmt).fetchall()]


@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)) -> Response:
    """
    Generate sitemap.xml with all public pages and gene detail pages.

    Public endpoint - no authentication required.
    Cached for 1 hour to avoid repeated DB queries.
    """
    global _sitemap_cache

    cached_xml, cached_at = _sitemap_cache
    if cached_xml and (time.time() - cached_at) < _CACHE_TTL:
        return Response(content=cached_xml, media_type="application/xml")

    symbols = await run_in_threadpool(lambda: _query_gene_symbols(db))
    xml_bytes = _build_sitemap_xml(symbols)
    _sitemap_cache = (xml_bytes, time.time())

    await logger.info("Sitemap generated", gene_count=len(symbols))

    return Response(content=xml_bytes, media_type="application/xml")
