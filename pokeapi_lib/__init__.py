# pokeapi_wrapper_lib/pokeapi_lib/__init__.py

# --- Core Functions ---
from .core import (
    get_pokemon,
    get_species,
    get_generation,
    get_type,
    get_evolution_chain, # Added
    get_all_generations,
    get_all_types
)

# --- Models ---
# Import main data models users might need type hints for
from .models import (
    BasePokemon,
    BaseSpecies,
    GenerationInfo,
    TypeInfo,
    EvolutionChain, # Added
    ChainLink,        # Added (needed for EvolutionChain structure)
    EvolutionDetail,  # Added (needed for EvolutionChain structure)
    NamedAPIResource, # Added (useful base type)
    PokemonTypeSlot,  # Added (part of BasePokemon)
    PokemonAbilitySlot, # Added (part of BasePokemon)
    PokemonStatData,    # Added (part of BasePokemon)
    SpriteData        # Added (part of BasePokemon)
    # Add others like FlavorText, Genus if library users might need them directly
)

# --- Exceptions ---
from .exceptions import (
    PokeAPIError,
    ResourceNotFoundError,
    PokeAPIConnectionError,
    CacheError
)

# --- Configuration / Setup ---
from .cache import configure_redis, close_redis_pool
# Optional: If you created a config_lib.py
# from .config_lib import settings as library_settings

# --- Version ---
# Keep version consistent with pyproject.toml
__version__ = "0.1.0"


# --- __all__ for explicit export control ---
# Lists all the names that should be imported when doing 'from pokeapi_lib import *'
# Also helpful for static analysis tools.
__all__ = [
    # Core Functions
    "get_pokemon",
    "get_species",
    "get_generation",
    "get_type",
    "get_evolution_chain",
    "get_all_generations",
    "get_all_types",

    # Config/Close
    "configure_redis",
    "close_redis_pool",
    # "library_settings", # Export if config_lib.py exists

    # Models (Export key models)
    "BasePokemon",
    "BaseSpecies",
    "GenerationInfo",
    "TypeInfo",
    "EvolutionChain",
    "ChainLink",
    "EvolutionDetail",
    "NamedAPIResource",
    "PokemonTypeSlot",
    "PokemonAbilitySlot",
    "PokemonStatData",
    "SpriteData",

    # Exceptions
    "PokeAPIError",
    "ResourceNotFoundError",
    "PokeAPIConnectionError",
    "CacheError",
]