"""
Test data factories using Factory Boy for DRY and maintainable test data.
Following KISS principle - simple, reusable test data generation.
"""

from datetime import datetime, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyFloat
from faker import Faker

from app.core.security import get_password_hash
from app.models.gene import Gene
from app.models.gene_staging import GeneNormalizationStaging
from app.models.user import User

fake = Faker()


class BaseFactory(SQLAlchemyModelFactory):
    """
    Base factory with session management.
    All factories should inherit from this.
    """

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class GeneFactory(BaseFactory):
    """Gene factory with realistic genomic data."""

    class Meta:
        model = Gene

    # Basic identifiers
    symbol = factory.LazyFunction(lambda: f"GENE{fake.random_int(1, 9999)}")
    hgnc_id = factory.LazyAttribute(lambda o: f"HGNC:{abs(hash(o.symbol)) % 100000}")
    ensembl_gene_id = factory.LazyAttribute(lambda o: f"ENSG{fake.random_number(11, fix_len=True)}")
    gene_name = factory.LazyAttribute(lambda o: f"{o.symbol} gene")

    # Evidence and classification
    evidence_score = FuzzyFloat(0.1, 1.0)
    classification = FuzzyChoice(["definitive", "strong", "moderate", "limited"])
    confidence_level = FuzzyChoice(["high", "moderate", "low"])

    # JSONB annotations with realistic structure
    annotations = factory.LazyFunction(
        lambda: {
            "panelapp": {
                "confidence": fake.random_element([3, 2, 1]),
                "mode_of_inheritance": fake.random_element(["AD", "AR", "XL", "MT"]),
                "panel_name": fake.random_element(["Cystic kidney disease", "FSGS", "CAKUT"]),
            },
            "clinvar": {
                "pathogenic": fake.random_int(0, 10),
                "likely_pathogenic": fake.random_int(0, 10),
                "vus": fake.random_int(0, 20),
                "conflicting": fake.random_int(0, 5),
            },
            "omim": {"mim_number": str(fake.random_number(6))},
            "hpo": {
                "terms": [
                    f"HP:{fake.random_number(7, fix_len=True)}"
                    for _ in range(fake.random_int(1, 5))
                ],
                "kidney_related": fake.boolean(chance_of_getting_true=80),
            },
        }
    )

    # Aggregated data
    aggregated_data = factory.LazyAttribute(
        lambda o: {
            "total_sources": fake.random_int(3, 9),
            "kidney_specificity_score": o.evidence_score * fake.pyfloat(0.5, 1.0),
            "publication_count": fake.random_int(0, 100),
            "last_updated": datetime.utcnow().isoformat(),
        }
    )

    # Timestamps
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-1y", end_date="now")
    )
    updated_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(days=fake.random_int(0, 30))
    )


class GeneNormalizationStagingFactory(BaseFactory):
    """Gene staging factory for testing data ingestion pipeline."""

    class Meta:
        model = GeneNormalizationStaging

    source = FuzzyChoice(["panelapp", "hpo", "clinvar", "clingen", "gencc", "pubtator"])
    raw_symbol = factory.LazyFunction(
        lambda: fake.random_element(["PKD1", "COL4A5", "NPHS1", f"GENE{fake.random_int(1, 999)}"])
    )
    normalized_symbol = factory.LazyAttribute(lambda o: o.raw_symbol.upper())
    hgnc_id = factory.LazyAttribute(lambda o: f"HGNC:{abs(hash(o.normalized_symbol)) % 100000}")

    data = factory.LazyFunction(
        lambda: {
            "raw_data": {
                "source_id": str(fake.uuid4()),
                "confidence": fake.random_int(1, 5),
                "evidence_count": fake.random_int(0, 50),
            },
            "metadata": {"ingested_at": datetime.utcnow().isoformat()},
        }
    )

    normalization_status = FuzzyChoice(["success", "partial", "failed", "pending"])
    normalization_log = factory.LazyAttribute(
        lambda o: {
            "status": o.normalization_status,
            "attempts": fake.random_int(1, 3),
            "message": "Normalized successfully"
            if o.normalization_status == "success"
            else "Normalization failed",
        }
    )

    created_at = factory.LazyFunction(datetime.utcnow)


class UserFactory(BaseFactory):
    """User factory with hashed passwords and roles."""

    class Meta:
        model = User

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    full_name = factory.Faker("name")

    # Hash a random password
    hashed_password = factory.LazyFunction(lambda: get_password_hash(fake.password(length=12)))

    role = FuzzyChoice(["admin", "curator", "public"])
    is_active = factory.Faker("boolean", chance_of_getting_true=90)

    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-6m", end_date="now")
    )
    last_login = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(days=fake.random_int(0, 7))
    )


# Batch creation helpers for common scenarios
class GeneFactoryBatch:
    """Helper class for creating batches of genes with specific characteristics."""

    @staticmethod
    def create_kidney_panel(session, count: int = 10) -> list[Gene]:
        """Create genes specifically for kidney disease testing."""
        genes = []
        kidney_genes = [
            "PKD1",
            "PKD2",
            "COL4A5",
            "COL4A3",
            "COL4A4",
            "NPHS1",
            "NPHS2",
            "WT1",
            "PAX2",
            "HNF1B",
        ]

        for i in range(min(count, len(kidney_genes))):
            gene = GeneFactory.build(
                symbol=kidney_genes[i],
                classification="definitive" if i < 5 else "strong",
                evidence_score=0.8 + (i * 0.02),
            )
            gene._session = session
            genes.append(gene)

        # Create additional random genes if needed
        for _ in range(count - len(genes)):
            gene = GeneFactory.build()
            gene._session = session
            genes.append(gene)

        session.add_all(genes)
        session.commit()

        return genes

    @staticmethod
    def create_with_varying_evidence(session, count: int = 20) -> list[Gene]:
        """Create genes with varying evidence scores for testing filters."""
        genes = []
        for i in range(count):
            # Create distribution across evidence scores
            score = i / count  # Linear distribution from 0 to 1
            classification = (
                "definitive"
                if score > 0.75
                else ("strong" if score > 0.5 else ("moderate" if score > 0.25 else "limited"))
            )

            gene = GeneFactory.build(evidence_score=score, classification=classification)
            gene._session = session
            genes.append(gene)

        session.add_all(genes)
        session.commit()

        return genes


class UserFactoryBatch:
    """Helper class for creating batches of users with specific roles."""

    @staticmethod
    def create_role_distribution(
        session, admins: int = 1, curators: int = 3, public: int = 6
    ) -> dict[str, list[User]]:
        """Create users with specific role distribution."""
        users = {"admin": [], "curator": [], "public": []}

        # Create admin users
        for i in range(admins):
            user = UserFactory.build(username=f"admin{i}", role="admin", is_active=True)
            user._session = session
            users["admin"].append(user)

        # Create curator users
        for i in range(curators):
            user = UserFactory.build(username=f"curator{i}", role="curator", is_active=True)
            user._session = session
            users["curator"].append(user)

        # Create public users
        for i in range(public):
            user = UserFactory.build(username=f"user{i}", role="public")
            user._session = session
            users["public"].append(user)

        # Add all users to session
        all_users = users["admin"] + users["curator"] + users["public"]
        session.add_all(all_users)
        session.commit()

        return users
