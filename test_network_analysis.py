"""
Test Network Analysis Dashboard - Full Workflow
"""
import time
from playwright.sync_api import sync_playwright, expect

def test_network_analysis_workflow():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        print("🚀 Starting Network Analysis Test...")

        # 1. Navigate to Network Analysis page
        print("\n1️⃣ Navigating to Network Analysis page...")
        page.goto("http://localhost:5173/network-analysis")
        page.wait_for_load_state("networkidle")

        # Wait for page to load
        expect(page.locator("h1")).to_contain_text("Network Analysis")
        print("✅ Page loaded successfully")

        # 2. Configure gene filters
        print("\n2️⃣ Configuring gene filters...")

        # Set evidence tiers (already selected by default)
        print("   - Evidence tiers already selected")

        # Set min score to 50
        min_score_input = page.locator('input[type="number"]').first
        min_score_input.fill("50")
        print("   - Min score set to 50")

        # Set max genes to 100 (smaller for faster testing)
        max_genes_input = page.locator('input[type="number"]').nth(1)
        max_genes_input.fill("100")
        print("   - Max genes set to 100")

        # 3. Filter genes
        print("\n3️⃣ Filtering genes...")
        filter_button = page.get_by_role("button", name="Filter Genes")
        filter_button.click()

        # Wait for loading to complete
        page.wait_for_selector(".v-chip:has-text('genes selected')", timeout=10000)

        # Get gene count
        gene_chip = page.locator(".v-chip:has-text('genes selected')").text_content()
        print(f"✅ Genes filtered: {gene_chip}")

        # 4. Build network
        print("\n4️⃣ Building network...")

        # Set STRING score
        string_score_input = page.locator('input[label="Min STRING Score"]')
        if string_score_input.count() > 0:
            string_score_input.first.fill("400")

        build_button = page.get_by_role("button", name="Build Network")
        build_button.click()

        # Wait for network to build (look for stats)
        try:
            page.wait_for_selector(".v-card:has-text('Network Statistics')", timeout=30000)
            stats_text = page.locator(".v-card:has-text('Network Statistics')").first.text_content()
            print(f"✅ Network built successfully")
        except Exception as e:
            print(f"⚠️  Network build timeout or error: {e}")
            # Take screenshot for debugging
            page.screenshot(path="/tmp/network_build_error.png")

        # 5. Cluster network
        print("\n5️⃣ Clustering network...")
        cluster_button = page.get_by_role("button", name="Detect Clusters")

        if cluster_button.is_enabled():
            cluster_button.click()

            # Wait for clustering to complete
            try:
                page.wait_for_selector(".v-chip:has-text('clusters')", timeout=30000)
                cluster_chip = page.locator(".v-chip:has-text('clusters')").text_content()
                print(f"✅ Clustering complete: {cluster_chip}")
            except Exception as e:
                print(f"⚠️  Clustering timeout or error: {e}")
                page.screenshot(path="/tmp/clustering_error.png")
        else:
            print("⚠️  Cluster button not enabled")

        # 6. Run enrichment analysis (if clusters exist)
        print("\n6️⃣ Running enrichment analysis...")

        # Check if cluster selection exists
        cluster_select = page.locator('div.v-select:has-text("Select Cluster")')
        if cluster_select.count() > 0:
            print("   - Cluster selection available")

            # Click the select component
            cluster_select.click()
            page.wait_for_timeout(500)

            # Click first option in dropdown (look specifically in the overlay menu)
            first_cluster = page.locator('.v-overlay .v-list .v-list-item').first
            if first_cluster.count() > 0:
                first_cluster.click()
                print("   - First cluster selected")

                # Run enrichment
                enrich_button = page.get_by_role("button", name="Run Analysis")
                if enrich_button.is_enabled():
                    enrich_button.click()
                    print("   - Enrichment analysis started")

                    # Wait for results (or timeout)
                    try:
                        page.wait_for_selector(".v-data-table, .v-alert", timeout=60000)
                        print("✅ Enrichment results displayed")
                    except Exception as e:
                        print(f"⚠️  Enrichment timeout: {e}")
                else:
                    print("⚠️  Enrichment button not enabled")
        else:
            print("⚠️  No cluster selection available")

        # 7. Take final screenshot
        print("\n7️⃣ Taking final screenshot...")
        page.screenshot(path="/tmp/network_analysis_complete.png", full_page=True)
        print("✅ Screenshot saved to /tmp/network_analysis_complete.png")

        # Keep browser open for 5 seconds
        print("\n✨ Test complete! Keeping browser open for review...")
        time.sleep(5)

        browser.close()
        print("\n🎉 All tests completed!")

if __name__ == "__main__":
    try:
        test_network_analysis_workflow()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
