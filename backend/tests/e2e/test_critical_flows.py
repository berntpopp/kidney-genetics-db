"""
End-to-end tests for critical business flows.
These tests verify complete user workflows from start to finish.
"""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.factories import GeneFactory


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserJourney:
    """Test complete user journeys through the application."""

    @pytest.mark.asyncio
    async def test_researcher_workflow(self, async_client: AsyncClient, db_session: Session):
        """
        Test a researcher's complete workflow:
        1. Browse public gene data
        2. Register for an account
        3. Login
        4. Search for specific genes
        5. View detailed annotations
        6. Export data
        """
        # Step 1: Browse public gene data without authentication
        response = await async_client.get("/api/genes")
        assert response.status_code == 200
        public_genes = response.json()["items"]
        assert len(public_genes) > 0

        # Step 2: Register for an account
        registration_data = {
            "username": "researcher1",
            "email": "researcher@university.edu",
            "password": "SecureResearch123!",
            "full_name": "Dr. Research",
        }

        reg_response = await async_client.post("/api/auth/register", json=registration_data)
        if reg_response.status_code == 404:
            pytest.skip("Registration endpoint not implemented")

        assert reg_response.status_code == 201

        # Step 3: Login to get access token
        login_response = await async_client.post(
            "/api/auth/login",
            data={
                "username": registration_data["username"],
                "password": registration_data["password"],
            },
        )

        if login_response.status_code == 404:
            pytest.skip("Login endpoint not implemented")

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Add authentication to client
        async_client.headers["Authorization"] = f"Bearer {token}"

        # Step 4: Search for kidney-specific genes
        search_response = await async_client.get(
            "/api/genes", params={"search": "PKD", "limit": 10}
        )
        assert search_response.status_code == 200
        search_results = search_response.json()

        # Step 5: View detailed annotations for a gene
        if search_results["items"]:
            gene_id = search_results["items"][0]["hgnc_id"]
            detail_response = await async_client.get(
                f"/api/genes/{gene_id}", params={"include_annotations": True}
            )
            assert detail_response.status_code == 200
            gene_details = detail_response.json()
            assert "annotations" in gene_details

        # Step 6: Export filtered data
        export_response = await async_client.get(
            "/api/genes/export",
            params={"format": "csv", "evidence_score_min": 0.5, "classification": "definitive"},
        )

        if export_response.status_code != 404:
            assert export_response.status_code == 200
            # CSV export should have appropriate content type
            assert (
                "csv" in export_response.headers.get("content-type", "").lower()
                or "download" in export_response.headers.get("content-disposition", "").lower()
            )


@pytest.mark.e2e
@pytest.mark.slow
class TestCuratorWorkflow:
    """Test curator-specific workflows."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Create test data for curation."""
        # Create genes that need curation
        self.pending_genes = GeneFactory.create_batch(
            5, classification="limited", _session=db_session
        )
        db_session.commit()

    @pytest.mark.asyncio
    async def test_gene_curation_process(self, curator_client: AsyncClient, db_session: Session):
        """
        Test the gene curation workflow:
        1. View genes pending curation
        2. Review gene evidence
        3. Update classification
        4. Add curator notes
        5. Approve for publication
        """
        # Step 1: Get genes needing curation
        response = await curator_client.get(
            "/api/genes", params={"classification": "limited", "sort": "evidence_score"}
        )
        assert response.status_code == 200
        genes_to_curate = response.json()["items"]

        if not genes_to_curate:
            pytest.skip("No genes available for curation")

        # Step 2: Review detailed evidence for first gene
        gene = genes_to_curate[0]
        detail_response = await curator_client.get(
            f"/api/genes/{gene['hgnc_id']}",
            params={"include_annotations": True, "include_evidence": True},
        )
        assert detail_response.status_code == 200

        # Step 3: Update gene classification based on evidence
        curation_data = {
            "classification": "moderate",
            "confidence_level": "high",
            "curator_notes": "Upgraded based on new PanelApp evidence",
            "evidence_summary": {
                "panelapp": "Green gene in multiple panels",
                "clinvar": "Multiple pathogenic variants",
                "literature": "Strong publication support",
            },
        }

        update_response = await curator_client.patch(
            f"/api/genes/{gene['hgnc_id']}/curate", json=curation_data
        )

        if update_response.status_code == 404:
            pytest.skip("Curation endpoint not implemented")

        assert update_response.status_code in [200, 204]

        # Step 4: Verify the update
        verify_response = await curator_client.get(f"/api/genes/{gene['hgnc_id']}")
        assert verify_response.status_code == 200
        updated_gene = verify_response.json()
        assert updated_gene["classification"] == "moderate"


@pytest.mark.e2e
@pytest.mark.slow
class TestDataPipelineFlow:
    """Test the complete data ingestion pipeline flow."""

    @pytest.mark.asyncio
    async def test_pipeline_execution_monitoring(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """
        Test complete pipeline execution with progress monitoring:
        1. Trigger pipeline start
        2. Monitor progress via WebSocket
        3. Verify data updates
        4. Check pipeline logs
        """
        # Step 1: Start the pipeline
        start_response = await admin_client.post("/api/pipeline/start")

        if start_response.status_code == 404:
            pytest.skip("Pipeline endpoint not implemented")

        assert start_response.status_code == 202  # Accepted
        job_data = start_response.json()
        job_id = job_data.get("job_id")

        # Step 2: Monitor progress (simulated - WebSocket would be better)
        max_attempts = 30
        for _attempt in range(max_attempts):
            progress_response = await admin_client.get(f"/api/pipeline/status/{job_id}")

            if progress_response.status_code == 200:
                status = progress_response.json()

                if status.get("status") == "completed":
                    break
                elif status.get("status") == "failed":
                    pytest.fail(f"Pipeline failed: {status.get('error')}")

            await asyncio.sleep(1)  # Wait before next check

        # Step 3: Verify data was updated
        stats_response = await admin_client.get("/api/statistics")

        if stats_response.status_code == 200:
            stats = stats_response.json()
            assert stats["total_genes"] > 0
            assert "last_pipeline_run" in stats

        # Step 4: Check pipeline logs
        logs_response = await admin_client.get(
            "/api/admin/logs", params={"category": "pipeline", "job_id": job_id}
        )

        if logs_response.status_code == 200:
            logs = logs_response.json()
            assert len(logs) > 0
            # Should have start and completion logs
            log_messages = [log["message"] for log in logs]
            assert any("started" in msg.lower() for msg in log_messages)


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorRecovery:
    """Test system behavior under error conditions."""

    @pytest.mark.asyncio
    async def test_api_error_handling(self, async_client: AsyncClient):
        """Test that API handles errors gracefully."""
        # Test invalid gene ID format
        response = await async_client.get("/api/genes/INVALID_ID_FORMAT")
        assert response.status_code in [400, 404]
        error_data = response.json()
        assert "detail" in error_data

        # Test SQL injection attempt (should be safe)
        response = await async_client.get(
            "/api/genes", params={"search": "'; DROP TABLE genes; --"}
        )
        assert response.status_code == 200  # Should handle safely

        # Test extremely large pagination
        response = await async_client.get("/api/genes", params={"limit": 999999, "offset": 999999})
        # Should either cap the limit or return empty results
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_concurrent_modifications(self, curator_client: AsyncClient, db_session: Session):
        """Test handling of concurrent data modifications."""
        # Create a test gene
        gene = GeneFactory.create(_session=db_session)
        db_session.commit()

        # Simulate two concurrent updates
        update1 = {"classification": "strong"}
        update2 = {"classification": "moderate"}

        # Send both updates concurrently
        tasks = [
            curator_client.patch(f"/api/genes/{gene.hgnc_id}/curate", json=update1),
            curator_client.patch(f"/api/genes/{gene.hgnc_id}/curate", json=update2),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Both should complete without database errors
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 204, 404]


@pytest.mark.e2e
@pytest.mark.critical
class TestCriticalDataIntegrity:
    """Test critical data integrity scenarios."""

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, admin_client: AsyncClient, db_session: Session):
        """Test that failed operations properly rollback."""
        initial_count_response = await admin_client.get("/api/genes")
        initial_count = initial_count_response.json()["total"]

        # Attempt to create gene with invalid data that should fail
        invalid_gene_data = {
            "symbol": None,  # Required field
            "evidence_score": 1.5,  # Out of range
            "classification": "invalid_class",
        }

        create_response = await admin_client.post("/api/genes", json=invalid_gene_data)

        # Should fail validation
        if create_response.status_code != 404:  # If endpoint exists
            assert create_response.status_code in [400, 422]

            # Verify count hasn't changed (transaction rolled back)
            final_count_response = await admin_client.get("/api/genes")
            final_count = final_count_response.json()["total"]
            assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_cache_consistency(self, async_client: AsyncClient, admin_client: AsyncClient):
        """Test that cache remains consistent with database."""
        # Get a gene
        genes_response = await async_client.get("/api/genes", params={"limit": 1})
        if not genes_response.json()["items"]:
            pytest.skip("No genes available")

        gene = genes_response.json()["items"][0]
        gene_id = gene["hgnc_id"]

        # Fetch gene (should cache it)
        response1 = await async_client.get(f"/api/genes/{gene_id}")
        original_data = response1.json()

        # Admin updates the gene (should invalidate cache)
        update_response = await admin_client.patch(
            f"/api/genes/{gene_id}", json={"evidence_score": 0.99}
        )

        if update_response.status_code != 404:
            # Fetch again (should get updated data, not cached)
            response2 = await async_client.get(f"/api/genes/{gene_id}")
            updated_data = response2.json()

            # Data should be different
            assert updated_data["evidence_score"] == 0.99
            assert updated_data["evidence_score"] != original_data.get("evidence_score")
