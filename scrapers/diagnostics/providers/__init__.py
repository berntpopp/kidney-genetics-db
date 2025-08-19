"""
Individual provider scrapers.
"""

from .blueprint_genetics import BlueprintGeneticsScraper
from .mayo_clinic import MayoClinicScraper
from .centogene import CentogeneScraper
from .cegat import CegatScraper
from .invitae import InvitaeScraper
from .mgz_muenchen import MGZMuenchenScraper
from .mvz_medicover import MVZMedicoverScraper
from .natera import NateraScraper
from .prevention_genetics import PreventionGeneticsScraper

__all__ = [
    'BlueprintGeneticsScraper',
    'MayoClinicScraper',
    'CentogeneScraper',
    'CegatScraper',
    'InvitaeScraper',
    'MGZMuenchenScraper',
    'MVZMedicoverScraper',
    'NateraScraper',
    'PreventionGeneticsScraper'
]
