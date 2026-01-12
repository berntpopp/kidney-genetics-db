"""
Test gene annotation models and functionality.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.gene import Gene
from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation


def unique_hgnc_id():
    """Generate a unique HGNC ID for testing."""
    return f"HGNC:TEST{uuid.uuid4().hex[:8].upper()}"


def test_annotation_source_creation(db_session: Session):
    """Test creating an annotation source."""
    source = AnnotationSource(
        source_name="test_source",
        display_name="Test Source",
        description="A test annotation source",
        update_frequency="daily",
        is_active=True,
        priority=5,
        config={"api_url": "https://example.com", "ttl_days": 7},
    )

    db_session.add(source)
    db_session.commit()

    assert source.id is not None
    assert source.source_name == "test_source"
    assert source.is_active is True
    assert source.config["ttl_days"] == 7


def test_gene_annotation_creation(db_session: Session):
    """Test creating a gene annotation."""
    # First create a gene with unique ID
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    # Create annotation
    annotation = GeneAnnotation(
        gene_id=gene.id,
        source="hgnc",
        version="2024.01",
        annotations={
            "ncbi_gene_id": "12345",
            "mane_select": {
                "ensembl_transcript_id": "ENST00000000001",
                "refseq_transcript_id": "NM_000001.1",
            },
            "omim_ids": ["123456"],
            "pubmed_ids": ["12345678", "87654321"],
        },
        source_metadata={"retrieved_at": "2024-01-15T10:00:00Z", "api_version": "v1"},
    )

    db_session.add(annotation)
    db_session.commit()

    assert annotation.id is not None
    assert annotation.gene_id == gene.id
    assert annotation.source == "hgnc"
    assert annotation.annotations["ncbi_gene_id"] == "12345"

    # Test the get_annotation_value helper
    assert annotation.get_annotation_value("ncbi_gene_id") == "12345"
    assert annotation.get_annotation_value("mane_select.ensembl_transcript_id") == "ENST00000000001"
    assert annotation.get_annotation_value("nonexistent", "default") == "default"


def test_gnomad_annotation(db_session: Session):
    """Test gnomAD constraint annotation."""
    # Create a gene with unique ID
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    # Create gnomAD annotation
    annotation = GeneAnnotation(
        gene_id=gene.id,
        source="gnomad",
        version="v4.0.0",
        annotations={
            "pli": 0.95,
            "oe_lof": 0.15,
            "oe_lof_upper": 0.20,
            "oe_lof_lower": 0.10,
            "lof_z": 3.5,
            "mis_z": 2.1,
            "syn_z": -0.5,
            "oe_mis": 0.75,
            "oe_syn": 1.05,
            "oe_mis_upper": 0.80,
            "oe_mis_lower": 0.70,
            "oe_syn_upper": 1.10,
            "oe_syn_lower": 1.00,
        },
    )

    db_session.add(annotation)
    db_session.commit()

    assert annotation.annotations["pli"] == 0.95
    assert annotation.annotations["lof_z"] == 3.5
    assert annotation.get_annotation_value("oe_lof") == 0.15


def test_annotation_history(db_session: Session):
    """Test annotation history tracking."""
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    history = AnnotationHistory(
        gene_id=gene.id,
        source="hgnc",
        operation="insert",
        new_data={"ncbi_gene_id": "99999"},
        changed_by="test_user",
        change_reason="Initial annotation",
    )

    db_session.add(history)
    db_session.commit()

    assert history.id is not None
    assert history.gene_id == gene.id
    assert history.operation == "insert"
    assert history.new_data["ncbi_gene_id"] == "99999"


def test_unique_constraint(db_session: Session):
    """Test unique constraint on gene_id, source, version."""
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    # First annotation
    ann1 = GeneAnnotation(
        gene_id=gene.id, source="hgnc", version="v1", annotations={"test": "data1"}
    )
    db_session.add(ann1)
    db_session.commit()

    # Duplicate should fail
    ann2 = GeneAnnotation(
        gene_id=gene.id, source="hgnc", version="v1", annotations={"test": "data2"}
    )
    db_session.add(ann2)

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # Different version should work
    ann3 = GeneAnnotation(
        gene_id=gene.id, source="hgnc", version="v2", annotations={"test": "data3"}
    )
    db_session.add(ann3)
    db_session.commit()

    assert ann3.id is not None


def test_annotation_source_update_check(db_session: Session):
    """Test checking if annotation source needs update."""
    from datetime import timedelta

    source = AnnotationSource(
        source_name="update_test",
        display_name="Update Test",
        last_update=datetime.utcnow() - timedelta(days=2),
        next_update=datetime.utcnow() - timedelta(days=1),
    )

    db_session.add(source)
    db_session.commit()

    # Should need update (next_update is in the past)
    assert source.is_update_due() is True

    # Update next_update to future
    source.next_update = datetime.utcnow() + timedelta(days=1)
    db_session.commit()

    assert source.is_update_due() is False
