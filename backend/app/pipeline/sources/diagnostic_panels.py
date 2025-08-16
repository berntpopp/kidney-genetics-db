"""
Diagnostic kidney panels data source integration

Integrates kidney gene panels from various diagnostic companies.
Since many companies don't provide APIs, this module uses manually
curated panel lists.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.crud.gene import gene_crud
from app.models.gene import GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


# Diagnostic panel data - manually curated from company websites
# Source: kidney-genetics-v1/analyses/03_DiagnosticPanels
DIAGNOSTIC_PANELS = {
    "Blueprint Genetics": {
        "url": "https://blueprintgenetics.com/tests/panels/nephrology/",
        "last_updated": "2024-01",
        "panels": [
            {
                "name": "Comprehensive Kidney Disease Panel",
                "genes": [
                    "ACTN4", "ADCK4", "AGXT", "ALMS1", "ANLN", "APOL1", "ARHGAP24",
                    "ARHGDIA", "BBS1", "BBS10", "BBS12", "BBS2", "BBS4", "BBS5",
                    "BBS7", "BBS9", "C3", "CD2AP", "CD46", "CFB", "CFH", "CFHR1",
                    "CFHR5", "CFI", "CLCN5", "COL4A3", "COL4A4", "COL4A5", "COQ2",
                    "COQ6", "COQ8B", "CRB2", "CUBN", "DSTYK", "DGKE", "EMP2", "EYA1",
                    "FAT1", "FN1", "GRHPR", "HNF1B", "HOGA1", "INF2", "INVS", "IQCB1",
                    "ITGA3", "ITGB4", "JAG1", "KANK1", "KANK2", "KANK4", "LAMB2",
                    "LMNA", "LMX1B", "LOXHD1", "LRP2", "MAFB", "MCP", "MEFV", "MKS1",
                    "MMACHC", "MTTL1", "MUC1", "MYH9", "MYO1E", "NEK8", "NEPH1",
                    "NPHP1", "NPHP3", "NPHP4", "NPHS1", "NPHS2", "NUP107", "NUP205",
                    "NUP93", "OCRL", "PAX2", "PDSS2", "PKD1", "PKD2", "PKHD1",
                    "PLG", "PLCE1", "PMM2", "PODXL", "PTPRO", "REN", "SCARB2",
                    "SDCCAG8", "SEC61A1", "SGPL1", "SIX1", "SIX2", "SLC12A1",
                    "SLC12A3", "SLC3A1", "SLC7A9", "SMARCAL1", "SYNPO", "THBD",
                    "TMEM67", "TNS2", "TRIM8", "TRPC6", "TTC21B", "TTC8", "UMOD",
                    "WDR19", "WDR73", "WT1", "XPO5", "ZMPSTE24"
                ],
            },
            {
                "name": "Alport Syndrome Panel",
                "genes": ["COL4A3", "COL4A4", "COL4A5", "MYH9", "EPAS1"],
            },
            {
                "name": "Nephrotic Syndrome Panel",
                "genes": [
                    "ACTN4", "ADCK4", "ANLN", "APOL1", "ARHGAP24", "ARHGDIA",
                    "CD2AP", "COL4A3", "COL4A4", "COL4A5", "COQ2", "COQ6", "COQ8B",
                    "CRB2", "CUBN", "DGKE", "EMP2", "INF2", "ITGA3", "ITGB4", "KANK1",
                    "KANK2", "KANK4", "LAMB2", "LMX1B", "MAFB", "MYH9", "MYO1E",
                    "NPHS1", "NPHS2", "NUP107", "NUP205", "NUP93", "PAX2", "PDSS2",
                    "PLG", "PLCE1", "PMM2", "PTPRO", "SCARB2", "SGPL1", "SMARCAL1",
                    "SYNPO", "TNS2", "TRIM8", "TRPC6", "TTC21B", "WT1", "XPO5"
                ],
            },
            {
                "name": "Polycystic Kidney Disease Panel",
                "genes": [
                    "ALG8", "ALG9", "ANKS6", "BICC1", "DNAJB11", "DZIP1L", "GANAB",
                    "HNF1B", "IFT140", "INVS", "JAG1", "LRP5", "NEK8", "NOTCH2",
                    "NPHP1", "NPHP3", "NPHP4", "PARN", "PKD1", "PKD2", "PKHD1",
                    "PMM2", "PRKCSH", "SEC61B", "SEC63", "UMOD", "VHL"
                ],
            },
        ],
    },
    "Natera Renasight": {
        "url": "https://www.natera.com/organ-health/renasight-genetic-testing/",
        "last_updated": "2024-01",
        "panels": [
            {
                "name": "Renasight Comprehensive Kidney Gene Panel",
                "genes": [
                    "AAAS", "AARS2", "ABCB11", "ABCC8", "ABHD5", "ACAD9", "ACADM",
                    "ACAT1", "ACE", "ACOX1", "ACTN4", "ADA2", "ADAMTS13", "ADAMTSL2",
                    "ADAR", "ADCK3", "ADCK4", "ADGRV1", "ADPRS", "ADRB1", "AFF4",
                    "AGA", "AGPAT2", "AGT", "AGTR1", "AGXT", "AGXT2", "AHI1", "AIFM1",
                    "AIPL1", "AIRE", "AKAP9", "AKR1D1", "ALDH18A1", "ALDH3A2",
                    "ALDH7A1", "ALDOB", "ALG1", "ALG13", "ALG3", "ALG6", "ALG8",
                    "ALG9", "ALMS1", "ALPL", "AMACR", "AMN", "ANGPTL3", "ANKS3",
                    "ANKS6", "ANLN", "ANO10", "AP1B1", "AP1S1", "AP2S1", "APOA1",
                    "APOB", "APOC2", "APOC3", "APOE", "APOL1", "APRT", "AQP2",
                    "ARFGEF2", "ARG1", "ARHGAP24", "ARHGDIA", "ARL13B", "ARL3",
                    "ARL6", "ARMC4", "ARSA", "ARSB", "ARSL", "ASAH1", "ASL", "ASNS",
                    "ASPA", "ASS1", "ATCAY", "ATM", "ATP13A2", "ATP1A1", "ATP1A3",
                    "ATP6AP2", "ATP6V0A2", "ATP6V0A4", "ATP6V1B1", "ATP6V1B2",
                    "ATP7A", "ATP7B", "ATP8B1", "ATPAF2", "ATR", "ATRX", "ATXN10",
                    "ATXN2", "ATXN7", "AUH", "AVPR2", "B3GLCT", "B9D1", "B9D2",
                    "BAAT", "BAG3", "BAP1", "BBIP1", "BBS1", "BBS10", "BBS12",
                    "BBS2", "BBS4", "BBS5", "BBS7", "BBS9", "BCAP31", "BCKDHA",
                    "BCKDHB", "BCL10", "BCOR", "BCS1L", "BICC1", "BIN1", "BLK",
                    "BLM", "BLNK", "BOLA3", "BPHL", "BRAF", "BRCA1", "BRCA2",
                    "BSCL2", "BSND", "BTD", "BTK", "C1QA", "C1QB", "C1QC", "C1R",
                    "C1S", "C2", "C3", "C4A", "C4B", "C5", "C5orf42", "C6", "C7",
                    "C8A", "C8B", "C8G", "C8orf37", "C9", "CA2", "CA4", "CA8",
                    "CACNA1A", "CACNA1S", "CARD11", "CARD14", "CARD9", "CASP10",
                    "CASP8", "CASR", "CAV1", "CBLIF", "CBS", "CC2D2A", "CCBE1",
                    "CCDC103", "CCDC114", "CCDC151", "CCDC28B", "CCDC39", "CCDC40",
                    "CCDC65", "CCDC78", "CCDC88C", "CCNO", "CCR5", "CD19", "CD247",
                    "CD27", "CD2AP", "CD3D", "CD3E", "CD3G", "CD40", "CD40LG",
                    "CD46", "CD55", "CD59", "CD70", "CD79A", "CD79B", "CD81",
                    "CD8A", "CD96", "CDAN1", "CDC42", "CDC73", "CDH1", "CDH23",
                    "CDK4", "CDKN1B", "CDKN1C", "CDKN2A", "CDKN2B", "CDON", "CEBPE",
                    "CEL", "CENPJ", "CEP104", "CEP120", "CEP164", "CEP19", "CEP290",
                    "CEP41", "CEP55", "CEP57", "CEP83", "CERKL", "CFAP221", "CFAP298",
                    "CFAP300", "CFAP43", "CFAP44", "CFAP52", "CFAP53", "CFAP54"
                ],
            },
        ],
    },
    "Centogene": {
        "url": "https://www.centogene.com/",
        "last_updated": "2024-01",
        "panels": [
            {
                "name": "CentoKidney Panel",
                "genes": [
                    "AARS2", "ABCB11", "ABCC8", "ABHD5", "ACAD9", "ACADM", "ACAT1",
                    "ACE", "ACOX1", "ACTN4", "ADA2", "ADAMTS13", "ADAMTSL2", "ADAR",
                    "ADCK3", "ADCK4", "ADGRV1", "ADPRS", "ADRB1", "AFF4", "AGA",
                    "AGPAT2", "AGT", "AGTR1", "AGXT", "AGXT2", "AHI1", "AIFM1",
                    "AIPL1", "AIRE", "AKAP9", "AKR1D1", "ALDH18A1", "ALDH3A2",
                    "ALDH7A1", "ALDOB", "ALG1", "ALG13", "ALG3", "ALG6", "ALG8",
                    "ALG9", "ALMS1", "ALPL", "AMACR", "AMN", "ANGPTL3", "ANKS3",
                    "ANKS6", "ANLN", "ANO10", "AP1B1", "AP1S1", "AP2S1", "APOA1",
                    "APOB", "APOC2", "APOC3", "APOE", "APOL1", "APRT", "AQP2"
                ],
            },
        ],
    },
    "Invitae": {
        "url": "https://www.invitae.com/",
        "last_updated": "2024-01",
        "panels": [
            {
                "name": "Invitae Comprehensive Kidney Disease Panel",
                "genes": [
                    "AAGAB", "AARS2", "ABCB11", "ABCC8", "ABHD5", "ACAD9", "ACADM",
                    "ACAT1", "ACE", "ACOX1", "ACTN4", "ADA2", "ADAMTS13", "ADAMTSL2",
                    "ADAR", "ADCK3", "ADCK4", "ADGRV1", "ADPRS", "ADRB1", "AFF4",
                    "AGA", "AGPAT2", "AGT", "AGTR1", "AGXT", "AGXT2", "AHI1", "AIFM1",
                    "AIPL1", "AIRE", "AKAP9", "AKR1D1", "ALDH18A1", "ALDH3A2",
                    "ALDH7A1", "ALDOB", "ALG1", "ALG13", "ALG3", "ALG6", "ALG8",
                    "ALG9", "ALMS1", "ALPL", "AMACR", "AMN", "ANGPTL3", "ANKS3",
                    "ANKS6", "ANLN", "ANO10", "AP1B1", "AP1S1", "AP2S1", "APOA1",
                    "APOB", "APOC2", "APOC3", "APOE", "APOL1", "APRT", "AQP2",
                    "ARFGEF2", "ARG1", "ARHGAP24", "ARHGDIA", "ARL13B", "ARL3",
                    "ARL6", "ARMC4", "ARSA", "ARSB", "ARSL", "ASAH1", "ASL", "ASNS",
                    "ASPA", "ASS1", "ATCAY", "ATM", "ATP13A2", "ATP1A1", "ATP1A3",
                    "ATP6AP2", "ATP6V0A2", "ATP6V0A4", "ATP6V1B1", "ATP6V1B2",
                    "ATP7A", "ATP7B", "ATP8B1", "ATPAF2", "ATR", "ATRX", "ATXN10",
                    "ATXN2", "ATXN7", "AUH", "AVPR2", "B3GLCT", "B9D1", "B9D2"
                ],
            },
        ],
    },
}


def update_diagnostic_panels_data(db: Session) -> dict[str, Any]:
    """Update database with diagnostic panel data

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    stats = {
        "source": "DiagnosticPanels",
        "companies_processed": 0,
        "panels_processed": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Process each company's panels
        gene_data_map = {}  # symbol -> {company_panels: set}

        for company_name, company_data in DIAGNOSTIC_PANELS.items():
            stats["companies_processed"] += 1
            logger.info(f"Processing {company_name} panels")

            for panel in company_data["panels"]:
                stats["panels_processed"] += 1
                panel_name = panel["name"]
                logger.info(f"Processing panel: {panel_name}")

                # Process genes in panel
                for gene_symbol in panel["genes"]:
                    if gene_symbol not in gene_data_map:
                        gene_data_map[gene_symbol] = {
                            "company_panels": [],
                            "all_genes": set(),
                        }

                    # Add panel info
                    panel_info = f"{company_name}: {panel_name}"
                    if panel_info not in gene_data_map[gene_symbol]["company_panels"]:
                        gene_data_map[gene_symbol]["company_panels"].append(panel_info)

                    # Track all genes in same panels (for network effects)
                    gene_data_map[gene_symbol]["all_genes"].update(panel["genes"])

        # Store in database
        for symbol, data in gene_data_map.items():
            stats["genes_processed"] += 1

            # Get or create gene
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene:
                # Create new gene
                try:
                    gene_create = GeneCreate(
                        approved_symbol=symbol,
                        hgnc_id=None,  # Would need HGNC lookup
                        aliases=[],
                    )
                    gene = gene_crud.create(db, gene_create)
                    stats["genes_created"] += 1
                    logger.info(f"Created new gene from diagnostic panels: {symbol}")
                except Exception as e:
                    logger.error(f"Error creating gene {symbol}: {e}")
                    stats["errors"] += 1
                    continue

            # Create or update evidence
            try:
                # Check if diagnostic panel evidence already exists
                existing = (
                    db.query(GeneEvidence)
                    .filter(
                        GeneEvidence.gene_id == gene.id,  # type: ignore[arg-type]
                        GeneEvidence.source_name == "DiagnosticPanels",
                    )
                    .first()
                )

                evidence_data = {
                    "panels": data["company_panels"],
                    "panel_count": len(data["company_panels"]),
                    "co_occurring_genes": list(data["all_genes"] - {symbol})[:50],  # Limit
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

                if existing:
                    # Update existing evidence
                    existing.evidence_data = evidence_data
                    existing.evidence_date = date.today()
                    existing.source_detail = f"{len(data['company_panels'])} diagnostic panels"
                    db.add(existing)
                else:
                    # Create new evidence
                    evidence = GeneEvidence(
                        gene_id=gene.id,  # type: ignore[arg-type]
                        source_name="DiagnosticPanels",
                        source_detail=f"{len(data['company_panels'])} diagnostic panels",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved diagnostic panel evidence for gene: {symbol}")

            except Exception as e:
                logger.error(f"Error saving diagnostic panel evidence for gene {symbol}: {e}")
                db.rollback()
                stats["errors"] += 1

    except Exception as e:
        logger.error(f"Error processing diagnostic panels: {e}")
        stats["errors"] += 1

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"Diagnostic panels update complete: {stats['companies_processed']} companies, "
        f"{stats['panels_processed']} panels, {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats
