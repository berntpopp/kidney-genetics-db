"""
Regression tests for configuration refactoring.

These tests ensure complete backward compatibility after extracting
configuration to YAML files. All existing APIs must work unchanged.
"""

from app.core.datasource_config import (
    ANNOTATION_COMMON_CONFIG,
    ANNOTATION_SOURCE_CONFIG,
    AUTO_UPDATE_SOURCES,
    DATA_SOURCE_CONFIG,
    INTERNAL_PROCESS_CONFIG,
    PRIORITY_ORDERED_SOURCES,
    get_all_source_names,
    get_annotation_config,
    get_auto_update_sources,
    get_internal_process_config,
    get_source_api_url,
    get_source_cache_ttl,
    get_source_config,
    get_source_parameter,
    is_source_configured,
)


class TestDataSourceConfigStructure:
    """Verify DATA_SOURCE_CONFIG maintains expected structure."""

    def test_all_sources_present(self):
        """All expected data sources should be present."""
        expected_sources = [
            "PanelApp",
            "PubTator",
            "ClinGen",
            "GenCC",
            "HPO",
            "DiagnosticPanels",
            "Literature",
        ]
        for source in expected_sources:
            assert source in DATA_SOURCE_CONFIG, f"Missing source: {source}"

    def test_source_config_structure(self):
        """Each source should have required fields."""
        required_fields = ["display_name", "description", "priority"]
        for source_name, config in DATA_SOURCE_CONFIG.items():
            for field in required_fields:
                assert field in config, f"Missing {field} in {source_name}"


class TestPanelAppConfig:
    """Verify PanelApp specific configuration."""

    def test_panelapp_basic_config(self):
        """Verify basic PanelApp configuration values."""
        config = get_source_config("PanelApp")
        assert config is not None
        assert config["display_name"] == "PanelApp"
        assert config["priority"] == 1
        assert config["auto_update"] is True
        assert config["cache_ttl"] == 21600  # 6 hours

    def test_panelapp_panel_ids(self):
        """Verify panel IDs are preserved."""
        config = get_source_config("PanelApp")
        assert config["uk_panels"] == [384, 539]
        assert config["au_panels"] == [217, 363]

    def test_panelapp_confidence_levels(self):
        """Verify confidence levels configuration."""
        config = get_source_config("PanelApp")
        assert config["confidence_levels"] == ["green", "amber"]
        assert config["min_evidence_level"] == 3

    def test_panelapp_api_urls(self):
        """Verify API URLs are present."""
        config = get_source_config("PanelApp")
        assert config["uk_api_url"] == "https://panelapp.genomicsengland.co.uk/api/v1"
        assert config["au_api_url"] == "https://panelapp-aus.org/api/v1"

    def test_panelapp_keywords(self):
        """Verify kidney keywords are applied to PanelApp."""
        config = get_source_config("PanelApp")
        assert "kidney_keywords" in config
        keywords = config["kidney_keywords"]
        assert "kidney" in keywords
        assert "renal" in keywords
        assert "nephro" in keywords
        assert len(keywords) == 18  # All deduplicated keywords


class TestPubTatorConfig:
    """Verify PubTator configuration."""

    def test_pubtator_basic_config(self):
        """Verify basic PubTator configuration."""
        config = get_source_config("PubTator")
        assert config["display_name"] == "PubTator3"
        assert config["priority"] == 2
        assert config["requests_per_second"] == 3.0

    def test_pubtator_search_config(self):
        """Verify PubTator search configuration."""
        config = get_source_config("PubTator")
        expected_query = (
            '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'
        )
        assert config["search_query"] == expected_query
        assert config["batch_size"] == 100
        assert config["chunk_size"] == 300

    def test_pubtator_update_modes(self):
        """Verify update modes configuration."""
        config = get_source_config("PubTator")
        assert config["smart_update"]["max_pages"] == 500
        assert config["smart_update"]["duplicate_threshold"] == 0.9
        assert config["full_update"]["max_pages"] is None


class TestClinGenConfig:
    """Verify ClinGen configuration."""

    def test_clingen_basic_config(self):
        """Verify basic ClinGen configuration."""
        config = get_source_config("ClinGen")
        assert config["display_name"] == "ClinGen"
        assert config["priority"] == 3
        assert config["cache_ttl"] == 86400  # 24 hours

    def test_clingen_affiliate_ids(self):
        """Verify kidney affiliate IDs are preserved."""
        config = get_source_config("ClinGen")
        expected_ids = [40066, 40068, 40067, 40069, 40070]
        assert config["kidney_affiliate_ids"] == expected_ids

    def test_clingen_api_urls(self):
        """Verify ClinGen API URLs."""
        config = get_source_config("ClinGen")
        assert config["api_url"] == "https://search.clinicalgenome.org/api"
        assert (
            config["download_url"] == "https://search.clinicalgenome.org/kb/gene-validity/download"
        )


class TestGenCCConfig:
    """Verify GenCC configuration."""

    def test_gencc_classification_weights(self):
        """Verify classification weights are preserved."""
        config = get_source_config("GenCC")
        weights = config["classification_weights"]
        assert weights["Definitive"] == 1.0
        assert weights["Strong"] == 0.8
        assert weights["Moderate"] == 0.6
        assert weights["Limited"] == 0.3
        assert weights["Refuted Evidence"] == 0.0

    def test_gencc_keywords(self):
        """Verify kidney keywords are applied to GenCC."""
        config = get_source_config("GenCC")
        assert "kidney_keywords" in config
        assert len(config["kidney_keywords"]) == 18


class TestHPOConfig:
    """Verify HPO configuration."""

    def test_hpo_phenotype_config(self):
        """Verify HPO phenotype configuration."""
        config = get_source_config("HPO")
        assert config["kidney_root_term"] == "HP:0010935"
        assert len(config["kidney_terms"]) == 4
        assert "HP:0000077" in config["kidney_terms"]

    def test_hpo_clinical_groups(self):
        """Verify HPO clinical groups are preserved."""
        config = get_source_config("HPO")
        groups = config["clinical_groups"]
        assert "complement" in groups
        assert "cakut" in groups
        assert "glomerulopathy" in groups
        assert groups["complement"]["weight"] == 1.0

    def test_hpo_onset_groups(self):
        """Verify HPO onset groups configuration."""
        config = get_source_config("HPO")
        onset = config["onset_groups"]
        assert onset["adult"]["root_term"] == "HP:0003581"
        assert onset["pediatric"]["root_terms"] == ["HP:0410280", "HP:0003623"]


class TestAnnotationConfig:
    """Verify annotation source configuration."""

    def test_annotation_sources_present(self):
        """All annotation sources should be present."""
        expected_sources = [
            "common",
            "gnomad",
            "clinvar",
            "hpo",
            "mpo_mgi",
            "hgnc",
            "string_ppi",
            "gtex",
            "descartes",
        ]
        for source in expected_sources:
            assert source in ANNOTATION_SOURCE_CONFIG, f"Missing annotation: {source}"

    def test_clinvar_config(self):
        """Verify ClinVar annotation configuration."""
        config = get_annotation_config("clinvar")
        assert config["requests_per_second"] == 2.8
        assert config["cache_ttl_days"] == 90
        assert config["gene_batch_size"] == 20
        assert config["variant_batch_size"] == 200

    def test_clinvar_review_confidence(self):
        """Verify ClinVar review confidence levels."""
        config = get_annotation_config("clinvar")
        confidence = config["review_confidence"]
        assert confidence["practice guideline"] == 4
        assert confidence["reviewed by expert panel"] == 4
        assert confidence["no classification provided"] == 0

    def test_common_config(self):
        """Verify common annotation configuration."""
        assert ANNOTATION_COMMON_CONFIG["default_timeout"] == 30.0
        assert ANNOTATION_COMMON_CONFIG["user_agent"] == "KidneyGeneticsDB/1.0"


class TestHelperFunctions:
    """Test all helper functions maintain backward compatibility."""

    def test_get_source_config(self):
        """Test get_source_config function."""
        config = get_source_config("PanelApp")
        assert config is not None
        assert config["display_name"] == "PanelApp"

        # Non-existent source
        assert get_source_config("NonExistent") is None

    def test_get_all_source_names(self):
        """Test get_all_source_names function."""
        names = get_all_source_names()
        assert "PanelApp" in names
        assert "PubTator" in names
        assert len(names) == 7

    def test_get_auto_update_sources(self):
        """Test automatic update sources list."""
        auto_sources = get_auto_update_sources()
        assert "PanelApp" in auto_sources
        assert "PubTator" in auto_sources
        assert "DiagnosticPanels" not in auto_sources  # manual upload

    def test_is_source_configured(self):
        """Test is_source_configured function."""
        assert is_source_configured("PanelApp") is True
        assert is_source_configured("NonExistent") is False

    def test_get_source_parameter(self):
        """Test get_source_parameter with direct and nested access."""
        # Direct parameter
        assert get_source_parameter("PanelApp", "display_name") == "PanelApp"
        assert get_source_parameter("PanelApp", "priority") == 1

        # Nested parameter with dot notation
        assert get_source_parameter("PubTator", "smart_update.max_pages") == 500
        assert get_source_parameter("HPO", "clinical_groups.complement.weight") == 1.0

        # Default value for non-existent
        assert get_source_parameter("PanelApp", "non_existent", "default") == "default"
        assert get_source_parameter("NonExistent", "param", 42) == 42

    def test_get_source_cache_ttl(self):
        """Test cache TTL retrieval."""
        assert get_source_cache_ttl("PanelApp") == 21600
        assert get_source_cache_ttl("ClinGen") == 86400
        assert get_source_cache_ttl("NonExistent") == 3600  # default

    def test_get_source_api_url(self):
        """Test API URL retrieval."""
        assert (
            get_source_api_url("PubTator") == "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
        )
        assert get_source_api_url("ClinGen") == "https://search.clinicalgenome.org/api"
        assert get_source_api_url("DiagnosticPanels") is None

    def test_get_internal_process_config(self):
        """Test internal process configuration."""
        config = get_internal_process_config("annotation_pipeline")
        assert config["display_name"] == "Gene Annotation Pipeline"
        assert config["category"] == "internal_process"


class TestGlobalVariables:
    """Test global variables maintain expected values."""

    def test_auto_update_sources_list(self):
        """Verify AUTO_UPDATE_SOURCES list."""
        assert isinstance(AUTO_UPDATE_SOURCES, list)
        assert "PanelApp" in AUTO_UPDATE_SOURCES
        assert "DiagnosticPanels" not in AUTO_UPDATE_SOURCES

    def test_priority_ordered_sources(self):
        """Verify sources are ordered by priority."""
        assert PRIORITY_ORDERED_SOURCES[0] == "PanelApp"  # priority 1
        assert PRIORITY_ORDERED_SOURCES[1] == "PubTator"  # priority 2
        assert PRIORITY_ORDERED_SOURCES[2] == "ClinGen"  # priority 3

    def test_internal_process_config(self):
        """Verify internal process configurations."""
        assert len(INTERNAL_PROCESS_CONFIG) == 3
        assert "annotation_pipeline" in INTERNAL_PROCESS_CONFIG
        assert "Evidence_Aggregation" in INTERNAL_PROCESS_CONFIG
        assert "HGNC_Normalization" in INTERNAL_PROCESS_CONFIG


class TestBackwardCompatibility:
    """Comprehensive tests to ensure no breaking changes."""

    def test_all_imports_work(self):
        """Verify all imports still work."""
        # This test passed by the fact that imports at top of file work
        assert DATA_SOURCE_CONFIG is not None
        assert ANNOTATION_SOURCE_CONFIG is not None
        assert callable(get_source_config)

    def test_data_types_unchanged(self):
        """Verify data types remain the same."""
        assert isinstance(DATA_SOURCE_CONFIG, dict)
        assert isinstance(ANNOTATION_SOURCE_CONFIG, dict)
        assert isinstance(AUTO_UPDATE_SOURCES, list)
        assert isinstance(PRIORITY_ORDERED_SOURCES, list)

    def test_critical_values_preserved(self):
        """Verify critical configuration values are unchanged."""
        # PubTator rate limit - CRITICAL
        assert get_source_parameter("PubTator", "requests_per_second") == 3.0

        # ClinVar NCBI rate limit
        assert get_annotation_config("clinvar")["requests_per_second"] == 2.8

        # Panel IDs must be exact
        assert get_source_parameter("PanelApp", "uk_panels") == [384, 539]

        # Affiliate IDs must be exact
        clingen_ids = get_source_parameter("ClinGen", "kidney_affiliate_ids")
        assert clingen_ids == [40066, 40068, 40067, 40069, 40070]
