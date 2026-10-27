"""
Individual provider scrapers.
"""

from .blueprint_genetics import BlueprintGeneticsScraper
from .cegat import CegatScraper
from .centogene import CentogeneScraper
from .invitae import InvitaeScraper
from .mayo_clinic import MayoClinicScraper
from .mgz_muenchen import MGZMuenchenScraper
from .mvz_medicover import MVZMedicoverScraper
from .natera import NateraScraper
from .prevention_genetics import PreventionGeneticsScraper
from .uchicago_genetics import UChicagoGeneticsScraper

__all__ = [
    'BlueprintGeneticsScraper',
    'MayoClinicScraper',
    'CentogeneScraper',
    'CegatScraper',
    'InvitaeScraper',
    'MGZMuenchenScraper',
    'MVZMedicoverScraper',
    'NateraScraper',
    'PreventionGeneticsScraper',
    'UChicagoGeneticsScraper',
]
