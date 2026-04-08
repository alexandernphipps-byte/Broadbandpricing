"""Base provider class."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from broadband_pricing.models import Plan, Location
from broadband_pricing.http_client import StealthSession


class BaseProvider(ABC):
    """Base class for all broadband providers."""

    name: str = ""
    provider_type: str = ""  # cable, ilec_fiber, starlink, fwa

    def __init__(self):
        self.logger = logging.getLogger(f"provider.{self.name}")
        self.session = StealthSession()

    def get_plans(self, location: Location) -> list[Plan]:
        """Get plans for a location. Tries scraping first, falls back to published."""
        try:
            plans = self.scrape_plans(location)
            if plans:
                self.logger.info(
                    f"Scraped {len(plans)} plans from {self.name} for {location.city_state}"
                )
                return plans
        except Exception as e:
            self.logger.warning(f"Scraping failed for {self.name}: {e}")

        self.logger.info(f"Using published pricing for {self.name} in {location.city_state}")
        return self.published_plans(location)

    @abstractmethod
    def scrape_plans(self, location: Location) -> Optional[list[Plan]]:
        """Attempt to scrape live pricing. Return None if scraping fails."""
        ...

    @abstractmethod
    def published_plans(self, location: Location) -> list[Plan]:
        """Return known published pricing as fallback."""
        ...
