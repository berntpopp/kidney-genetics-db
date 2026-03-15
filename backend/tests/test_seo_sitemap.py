"""Tests for SEO sitemap endpoint."""

from xml.etree import ElementTree

import pytest


@pytest.mark.unit
class TestSitemap:
    """Sitemap generation tests."""

    @pytest.fixture(autouse=True)
    def _clear_sitemap_cache(self):
        """Clear the module-level sitemap cache before each test."""
        import app.api.endpoints.seo as seo_mod
        from app.api.endpoints.seo import _sitemap_cache  # noqa: F401

        seo_mod._sitemap_cache = (b"", 0.0)
        yield
        seo_mod._sitemap_cache = (b"", 0.0)

    @pytest.mark.asyncio
    async def test_sitemap_returns_xml(self, async_client):
        """GET /sitemap.xml returns valid XML."""
        response = await async_client.get("/sitemap.xml")
        assert response.status_code == 200
        assert "application/xml" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_sitemap_contains_static_pages(self, async_client):
        """Sitemap includes all static pages."""
        response = await async_client.get("/sitemap.xml")
        content = response.content.decode()
        for path in [
            "/",
            "/genes",
            "/dashboard",
            "/data-sources",
            "/network-analysis",
            "/about",
        ]:
            assert f"kidney-genetics.org{path}<" in content

    @pytest.mark.asyncio
    async def test_sitemap_has_lastmod(self, async_client):
        """Sitemap URLs should include lastmod timestamps."""
        response = await async_client.get("/sitemap.xml")
        root = ElementTree.fromstring(response.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall("s:url", ns)
        assert len(urls) > 0
        # Static pages (first 6) should have lastmod
        for url in urls[:6]:
            lastmod = url.find("s:lastmod", ns)
            loc_text = url.find("s:loc", ns).text  # type: ignore[union-attr]
            assert lastmod is not None, f"Missing lastmod for {loc_text}"

    @pytest.mark.asyncio
    async def test_sitemap_has_cache_control(self, async_client):
        """Sitemap response should include Cache-Control header."""
        response = await async_client.get("/sitemap.xml")
        assert "cache-control" in response.headers
        assert "public" in response.headers["cache-control"]

    @pytest.mark.asyncio
    async def test_sitemap_gene_pages_have_structure_urls(self, async_client):
        """Gene pages should also have /structure sub-pages in sitemap."""
        response = await async_client.get("/sitemap.xml")
        root = ElementTree.fromstring(response.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall("s:url", ns)
        locs = [url.find("s:loc", ns).text for url in urls]  # type: ignore[union-attr]
        # Find any gene URL and check for matching structure URL
        gene_locs = [loc for loc in locs if loc and "/genes/" in loc and "/structure" not in loc]
        if gene_locs:
            symbol = gene_locs[0].split("/genes/")[-1]  # type: ignore[union-attr]
            structure_url = f"kidney-genetics.org/genes/{symbol}/structure"
            assert any(structure_url in loc for loc in locs if loc), (
                f"Missing structure URL for gene {symbol}"
            )
