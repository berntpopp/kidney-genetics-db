"""
Gene annotation sources module.
"""

from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource

__all__ = [
    "BaseAnnotationSource",
    "ClinVarAnnotationSource",
    "DescartesAnnotationSource",
    "EnsemblAnnotationSource",
    "GnomADAnnotationSource",
    "GTExAnnotationSource",
    "HGNCAnnotationSource",
    "HPOAnnotationSource",
    "MPOMGIAnnotationSource",
    "StringPPIAnnotationSource",
    "UniProtAnnotationSource",
]
