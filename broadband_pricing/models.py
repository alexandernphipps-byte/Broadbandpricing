"""Data models for broadband pricing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Plan:
    """A broadband plan offered by a provider."""

    provider: str
    provider_type: str  # cable, ilec_fiber, starlink, fwa
    plan_name: str
    speed_down: int  # Mbps
    speed_up: int  # Mbps
    monthly_price: float
    is_introductory: bool = False
    intro_duration_months: int = 0
    regular_price: Optional[float] = None

    @property
    def speed_label(self) -> str:
        if self.speed_down >= 1000:
            return f"{self.speed_down / 1000:.0f} Gig"
        return f"{self.speed_down} Mbps"


@dataclass
class PricingRecord:
    """A stored pricing record from a check."""

    id: Optional[int] = None
    timestamp: str = ""
    city: str = ""
    state: str = ""
    address: str = ""
    zip_code: str = ""
    provider: str = ""
    provider_type: str = ""
    plan_name: str = ""
    speed_down: int = 0
    speed_up: int = 0
    monthly_price: float = 0.0
    is_introductory: bool = False
    intro_duration_months: int = 0
    regular_price: Optional[float] = None
    source: str = "published"  # scraped or published


@dataclass
class Location:
    """A location to check pricing for."""

    city: str
    state: str
    address: str
    zip_code: str
    providers: dict = field(default_factory=dict)

    @property
    def full_address(self) -> str:
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"

    @property
    def city_state(self) -> str:
        return f"{self.city}, {self.state}"
