"""Tests for Pydantic v2 compliance."""

import ast
import pathlib

import pytest


@pytest.mark.unit
class TestPydanticV2Config:
    """Verify no deprecated class Config patterns remain."""

    SCHEMA_FILES = [
        "app/schemas/gene.py",
        "app/schemas/releases.py",
        "app/schemas/gene_staging.py",
        "app/schemas/auth.py",
    ]

    def test_no_class_config_in_schemas(self):
        """No schema file should have 'class Config:' pattern."""
        base = pathlib.Path("app/schemas")
        for schema_file in base.glob("*.py"):
            source = schema_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "Config":
                    pytest.fail(
                        f"Found deprecated 'class Config:' in {schema_file.name}. "
                        "Use 'model_config = ConfigDict(...)' instead."
                    )

    def test_model_config_used(self):
        """Verify model_config = ConfigDict is used."""
        for rel_path in self.SCHEMA_FILES:
            source = pathlib.Path(rel_path).read_text()
            if "from_attributes" in source:
                assert "model_config" in source, (
                    f"{rel_path} uses from_attributes but not model_config"
                )
