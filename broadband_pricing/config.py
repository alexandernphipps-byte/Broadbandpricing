"""Configuration for broadband pricing checker."""

from broadband_pricing.models import Location

# 10 US cities geographically spread across the country
# Each city has: cable operator, ILEC fiber, Starlink, and FWA provider
LOCATIONS = [
    Location(
        city="New York",
        state="NY",
        address="330 E 86th St",
        zip_code="10028",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "verizon_fios",
            "starlink": "starlink",
            "fwa": "verizon_5g",
        },
    ),
    Location(
        city="Los Angeles",
        state="CA",
        address="5410 Wilshire Blvd",
        zip_code="90036",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Chicago",
        state="IL",
        address="1560 N Sandburg Terrace",
        zip_code="60610",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Dallas",
        state="TX",
        address="3839 McKinney Ave",
        zip_code="75204",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "att_air",
        },
    ),
    Location(
        city="Seattle",
        state="WA",
        address="1521 2nd Ave",
        zip_code="98101",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Denver",
        state="CO",
        address="1550 Larimer St",
        zip_code="80202",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Atlanta",
        state="GA",
        address="201 17th St NW",
        zip_code="30363",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "att_air",
        },
    ),
    Location(
        city="Miami",
        state="FL",
        address="1200 Brickell Ave",
        zip_code="33131",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Phoenix",
        state="AZ",
        address="2323 N Central Ave",
        zip_code="85004",
        providers={
            "cable": "cox",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Minneapolis",
        state="MN",
        address="1225 LaSalle Ave",
        zip_code="55403",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "verizon_5g",
        },
    ),
]

# Provider display names
PROVIDER_NAMES = {
    "xfinity": "Xfinity",
    "spectrum": "Spectrum",
    "cox": "Cox",
    "att_fiber": "AT&T Fiber",
    "verizon_fios": "Verizon Fios",
    "quantum_fiber": "Quantum Fiber",
    "starlink": "Starlink",
    "tmobile_home": "T-Mobile Home Internet",
    "verizon_5g": "Verizon 5G Home",
    "att_air": "AT&T Internet Air",
}

# Provider type display names
PROVIDER_TYPE_NAMES = {
    "cable": "Cable",
    "ilec_fiber": "ILEC Fiber",
    "starlink": "Starlink",
    "fwa": "FWA",
}

# Schedule time for daily checks (24-hour format)
DAILY_CHECK_TIME = "06:00"

# Database path
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "pricing.db")

# Output directory for charts
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
