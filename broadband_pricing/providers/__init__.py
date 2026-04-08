"""Provider registry - maps provider keys to their classes."""

from broadband_pricing.providers.starlink import StarlinkProvider
from broadband_pricing.providers.xfinity import XfinityProvider
from broadband_pricing.providers.spectrum import SpectrumProvider
from broadband_pricing.providers.cox import CoxProvider
from broadband_pricing.providers.att_fiber import AttFiberProvider
from broadband_pricing.providers.verizon_fios import VerizonFiosProvider
from broadband_pricing.providers.quantum_fiber import QuantumFiberProvider
from broadband_pricing.providers.tmobile_home import TMobileHomeProvider
from broadband_pricing.providers.verizon_5g import Verizon5GProvider
from broadband_pricing.providers.att_air import AttAirProvider

# Registry mapping provider keys (used in config) to provider classes
PROVIDER_REGISTRY = {
    "starlink": StarlinkProvider,
    "xfinity": XfinityProvider,
    "spectrum": SpectrumProvider,
    "cox": CoxProvider,
    "att_fiber": AttFiberProvider,
    "verizon_fios": VerizonFiosProvider,
    "quantum_fiber": QuantumFiberProvider,
    "tmobile_home": TMobileHomeProvider,
    "verizon_5g": Verizon5GProvider,
    "att_air": AttAirProvider,
}

# Cached provider instances
_instances = {}


def get_provider(key: str):
    """Get a provider instance by key."""
    if key not in _instances:
        cls = PROVIDER_REGISTRY.get(key)
        if cls is None:
            raise ValueError(f"Unknown provider: {key}")
        _instances[key] = cls()
    return _instances[key]
