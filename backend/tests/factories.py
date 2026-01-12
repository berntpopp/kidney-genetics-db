"""
Test data factories using Factory Boy for DRY and maintainable test data.
Following KISS principle - simple, reusable test data generation.
"""

from datetime import datetime, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.fuzzy import FuzzyChoice
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
    """
    Gene factory matching the actual Gene model schema.

    The Gene model only has:
    - id (BigInteger, auto-generated)
    - hgnc_id (String)
    - approved_symbol (String, required)
    - aliases (ARRAY of Text)
    - valid_from/valid_to (TIMESTAMP, server defaults)
    - created_at/updated_at (from TimestampMixin)

    Note: evidence_score, classification, etc. are in GeneCuration, not Gene.
    """

    class Meta:
        model = Gene

    # Core identifiers matching actual Gene model - use UUID for guaranteed uniqueness
    approved_symbol = factory.LazyFunction(
        lambda: f"TG{fake.uuid4()[:8].upper().replace('-', '')}"
    )
    hgnc_id = factory.LazyFunction(
        lambda: f"HGNC:T{fake.uuid4()[:10].upper().replace('-', '')}"
    )

    # Aliases as an array of strings
    aliases = factory.LazyFunction(
        lambda: [f"ALIAS{fake.random_int(1, 999)}" for _ in range(fake.random_int(0, 3))]
    )

    # Timestamps (valid_from and valid_to have server defaults, so we don't set them)
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
    """
    Helper class for creating batches of genes with specific characteristics.

    Note: The Gene model only contains basic identifiers (hgnc_id, approved_symbol, aliases).
    Evidence scores and classifications are stored in GeneCuration, not Gene.
    These helpers create Gene records with appropriate symbols for testing.
    """

    @staticmethod
    def create_kidney_panel(session, count: int = 10) -> list[Gene]:
        """Create genes specifically for kidney disease testing."""
        import uuid
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
            # Use unique HGNC ID to avoid conflicts with dev database
            unique_id = uuid.uuid4().hex[:8].upper()
            gene = GeneFactory.build(
                approved_symbol=f"T{kidney_genes[i]}_{unique_id}",
                hgnc_id=f"HGNC:TK{unique_id}",
                aliases=[f"{kidney_genes[i]}_alias"],
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
        """
        Create genes for testing.

        Note: The Gene model doesn't have evidence_score or classification fields.
        Those are in GeneCuration. This method creates basic Gene records.
        """
        import uuid
        genes = []
        for i in range(count):
            # Use unique HGNC ID to avoid conflicts with dev database
            unique_id = uuid.uuid4().hex[:8].upper()
            gene = GeneFactory.build(
                approved_symbol=f"TGENE{i}_{unique_id}",
                hgnc_id=f"HGNC:TV{unique_id}",
            )
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
