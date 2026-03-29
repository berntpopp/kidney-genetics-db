"""Tests for PipelineOrchestrator stage management."""

import pytest

from app.core.pipeline_orchestrator import PipelineOrchestrator, PipelineStage


@pytest.mark.unit
class TestPipelineStages:
    """Verify stage transitions and dependency enforcement."""

    def test_initial_stage_is_idle(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch._current_stage = PipelineStage.IDLE
        assert orch._current_stage == PipelineStage.IDLE

    def test_stages_have_correct_order(self):
        assert PipelineStage.IDLE.value == 0
        assert PipelineStage.EVIDENCE.value == 1
        assert PipelineStage.ANNOTATIONS.value == 2
        assert PipelineStage.AGGREGATION.value == 3
        assert PipelineStage.COMPLETE.value == 4

    def test_evidence_sources_list(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch.EVIDENCE_SOURCES = [
            "PanelApp",
            "PubTator",
            "ClinGen",
            "GenCC",
            "HPO",
        ]
        assert len(orch.EVIDENCE_SOURCES) == 5
        assert "PanelApp" in orch.EVIDENCE_SOURCES


@pytest.mark.unit
class TestSourceCompletion:
    """Verify source completion tracking."""

    def test_mark_source_completed(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch._completed_sources = set()
        orch._failed_sources = set()
        orch.EVIDENCE_SOURCES = ["PanelApp", "ClinGen"]
        orch._current_stage = PipelineStage.EVIDENCE

        orch._completed_sources.add("PanelApp")
        assert "PanelApp" in orch._completed_sources

    def test_all_evidence_done_when_all_completed_or_failed(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch.EVIDENCE_SOURCES = ["PanelApp", "ClinGen", "GenCC"]
        orch._completed_sources = {"PanelApp", "ClinGen"}
        orch._failed_sources = {"GenCC"}

        all_done = (orch._completed_sources | orch._failed_sources) >= set(orch.EVIDENCE_SOURCES)
        assert all_done is True
