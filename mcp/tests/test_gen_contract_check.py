"""Tests for read-only generated-contract verification."""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def contract_generator() -> Iterator[ModuleType]:
    """Load the contract generator without running its CLI entry point."""
    script = Path(__file__).resolve().parents[1] / "scripts" / "gen_contract.py"
    spec = importlib.util.spec_from_file_location("gen_contract", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


@pytest.fixture
def committed_contract_dir(tmp_path: Path, contract_generator: ModuleType) -> Path:
    """Create a clean, standalone copy of the generated contract artifacts."""
    committed_dir = tmp_path / "committed"
    generated = contract_generator.generate_contract(committed_dir)
    assert {path.name for path in generated} == {
        "_generated_paths.py",
        "_generated_enums.py",
        "_generated_models.py",
    }
    return committed_dir


def test_verify_contract_accepts_current_artifacts_without_writing_them(
    contract_generator: ModuleType, committed_contract_dir: Path
) -> None:
    """Fresh artifacts pass verification and remain byte-identical."""
    before = {path.name: path.read_bytes() for path in committed_contract_dir.iterdir()}

    assert contract_generator.verify_contract(committed_contract_dir) == []

    assert {
        path.name: path.read_bytes() for path in committed_contract_dir.iterdir()
    } == before


def test_verify_contract_reports_stale_artifact_without_overwriting_it(
    contract_generator: ModuleType, committed_contract_dir: Path
) -> None:
    """A stale artifact fails verification but is never regenerated in place."""
    stale_path = committed_contract_dir / "_generated_paths.py"
    stale_path.write_text("stale contract artifact\n", encoding="utf-8")

    assert contract_generator.verify_contract(committed_contract_dir) == [stale_path]
    assert stale_path.read_text(encoding="utf-8") == "stale contract artifact\n"
