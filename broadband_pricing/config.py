"""Configuration for broadband pricing checker."""

from broadband_pricing.models import Location

# 24 US cities geographically spread across the country
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
    # --- Newly added cities ---
    Location(
        city="Stamford",
        state="CT",
        address="1 Landmark Square",
        zip_code="06901",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "verizon_fios",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Orlando",
        state="FL",
        address="400 S Orange Ave",
        zip_code="32801",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="San Antonio",
        state="TX",
        address="100 W Houston St",
        zip_code="78205",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "att_air",
        },
    ),
    Location(
        city="San Diego",
        state="CA",
        address="402 W Broadway",
        zip_code="92101",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Las Vegas",
        state="NV",
        address="300 S 4th St",
        zip_code="89101",
        providers={
            "cable": "cox",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Evanston",
        state="IL",
        address="1800 Sherman Ave",
        zip_code="60201",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Hartford",
        state="CT",
        address="100 Pearl St",
        zip_code="06103",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Fargo",
        state="ND",
        address="101 Broadway N",
        zip_code="58102",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="El Paso",
        state="TX",
        address="100 N Stanton St",
        zip_code="79901",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "att_air",
        },
    ),
    Location(
        city="Kansas City",
        state="MO",
        address="1 Pershing Rd",
        zip_code="64108",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Springfield",
        state="MO",
        address="830 Boonville Ave",
        zip_code="65802",
        providers={
            "cable": "spectrum",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Jacksonville",
        state="FL",
        address="220 E Bay St",
        zip_code="32202",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Portland",
        state="OR",
        address="1000 SW Broadway",
        zip_code="97205",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "quantum_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
        },
    ),
    Location(
        city="Madison",
        state="WI",
        address="1 S Pinckney St",
        zip_code="53703",
        providers={
            "cable": "xfinity",
            "ilec_fiber": "att_fiber",
            "starlink": "starlink",
            "fwa": "tmobile_home",
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
DAILY_CHECK_TIME = "09:00"

# Database path
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "pricing.db")

# Output directory for charts
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
