# pokeapi_lib/core.py
import httpx
import logging
import asyncio # Ensure asyncio is imported
from typing import Optional, Dict, Any, List, Union
from functools import lru_cache # Import lru_cache

from .client import fetch_resource, DEFAULT_BASE_URL, DEFAULT_TIMEOUT
from .cache import get_cache, set_cache
from .models import BasePokemon, BaseSpecies, GenerationInfo, TypeInfo, EvolutionChain
from .exceptions import ResourceNotFoundError, PokeAPIError, CacheError

logger = logging.getLogger(__name__)

# Default TTL for library cache (can be overridden)
DEFAULT_LIB_CACHE_TTL = 60 * 60 * 24 * 7 # 1 week

async def get_pokemon(
    identifier: Union[str, int],
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL,
) -> BasePokemon:
    """
    Fetches core data for a specific Pokémon by name or ID.

    Args:
        identifier: The Pokémon's name (string) or ID (int).
        client: An active httpx.AsyncClient instance.
        base_url: Base URL for the PokeAPI.
        cache_ttl: Cache duration in seconds.

    Returns:
        A BasePokemon Pydantic model instance.

    Raises:
        ResourceNotFoundError: If the Pokémon is not found.
        PokeAPIError: For other connection or processing errors.
    """
    identifier_str = str(identifier).lower()
    cache_key = f"pokeapi_lib:pokemon:{identifier_str}"
    endpoint = f"/pokemon/{identifier_str}"

    # 1. Check Cache
    cached_data = await get_cache(cache_key)
    if cached_data:
        try:
            return BasePokemon.model_validate(cached_data) # Validate cached data
        except Exception as e:
            logger.warning(f"Invalid cache data for {cache_key}, refetching. Error: {e}")
            # Optionally delete invalid cache here

    # 2. Fetch from API
    try:
        raw_data = await fetch_resource(endpoint, client, base_url)
    except ResourceNotFoundError:
        raise # Re-raise specific not found error
    except Exception as e:
        raise PokeAPIError(f"Failed to fetch Pokemon data for '{identifier}'") from e

    # 3. Validate and Model Data
    try:
        # Extract/transform specific fields if needed before validation
        #if raw_data.get('sprites'):
        #    raw_data['sprites']['official_artwork_front'] = raw_data['sprites'].get('other', {}).get('official-artwork', {}).get('front_default')

        pokemon = BasePokemon.model_validate(raw_data)
    except Exception as e:
        logger.error(f"Failed to validate Pokemon data for '{identifier}'. Error: {e}", exc_info=True)
        # logger.debug(f"Raw data: {raw_data}") # Debug raw data if validation fails
        raise PokeAPIError(f"Data validation failed for Pokemon '{identifier}'") from e

    # 4. Cache Result
    await set_cache(cache_key, pokemon.model_dump(mode='json'), ttl=cache_ttl)

    return pokemon


async def get_species(
    identifier: Union[str, int],
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL,
) -> BaseSpecies:
    """Fetches core data for a specific Pokémon species by name or ID."""
    identifier_str = str(identifier).lower()
    cache_key = f"pokeapi_lib:species:{identifier_str}"
    endpoint = f"/pokemon-species/{identifier_str}" # Use species endpoint

    cached_data = await get_cache(cache_key)
    if cached_data:
        try: return BaseSpecies.model_validate(cached_data)
        except Exception as e: logger.warning(f"Invalid cache for {cache_key}: {e}")

    try:
        raw_data = await fetch_resource(endpoint, client, base_url)
        species = BaseSpecies.model_validate(raw_data)
        await set_cache(cache_key, species.model_dump(mode='json'), ttl=cache_ttl)
        return species
    except ResourceNotFoundError: raise
    except Exception as e:
         logger.error(f"Error processing species '{identifier}': {e}", exc_info=True)
         raise PokeAPIError(f"Failed to get/process species '{identifier}'") from e

# --- MOVE Helper from backend ---
@lru_cache(maxsize=16)
def _generation_name_to_id(generation_name: Optional[str]) -> Optional[int]:
    """ Converts generation name (e.g., 'generation-i') to ID (e.g., 1)."""
    # ... (Keep the robust implementation with roman numeral mapping) ...
    if not generation_name: return None
    roman_to_int_map = {"i": 1,"ii": 2,"iii": 3,"iv": 4,"v": 5,"vi": 6,"vii": 7,"viii": 8,"ix": 9,}
    try:
        parts = generation_name.lower().split('-')
        if len(parts) != 2 or not parts[1]: return None
        roman_numeral = parts[1]
        generation_id = roman_to_int_map.get(roman_numeral)
        if generation_id is None: logger.warning(f"Unknown Roman numeral '{roman_numeral}'")
        return generation_id
    except Exception as e:
        logger.error(f"Error converting generation name '{generation_name}': {e}")
        return None

# --- Get Single Generation ---
async def get_generation(
    identifier: Union[str, int],
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL,
) -> GenerationInfo:
    """Fetches data for a specific Pokémon Generation by ID or name."""
    identifier_str = str(identifier).lower()
    cache_key = f"pokeapi_lib:generation:{identifier_str}"
    endpoint = f"/generation/{identifier_str}"

    cached_data = await get_cache(cache_key)
    if cached_data:
        try: return GenerationInfo.model_validate(cached_data)
        except Exception as e: logger.warning(f"Invalid cache for {cache_key}: {e}")

    try:
        raw_data = await fetch_resource(endpoint, client, base_url)

        # Extract necessary info
        gen_id_from_name = _generation_name_to_id(raw_data.get('name'))
        if gen_id_from_name is None: # Use ID from response if name parsing fails
             gen_id = raw_data.get('id')
        else:
             gen_id = gen_id_from_name

        if gen_id is None: # Still no ID? Cannot proceed
             raise PokeAPIError(f"Could not determine ID for generation '{identifier_str}'")

        region_info = raw_data.get('main_region')
        region_name = region_info.get('name', 'unknown') if region_info else 'unknown'

        gen_info = GenerationInfo(
            id=gen_id,
            name=raw_data.get('name', f'generation-{gen_id}'), # Ensure name field present
            region_name=region_name
        )

        await set_cache(cache_key, gen_info.model_dump(mode='json'), ttl=cache_ttl)
        return gen_info
    except ResourceNotFoundError: raise
    except Exception as e:
         logger.error(f"Error processing generation '{identifier}': {e}", exc_info=True)
         raise PokeAPIError(f"Failed to get/process generation '{identifier}'") from e

# --- Get Single Type ---
async def get_type(
    name: str,
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL,
) -> TypeInfo:
    """Fetches data for a specific Pokémon Type by name."""
    name_lower = name.lower()
    cache_key = f"pokeapi_lib:type:{name_lower}"
    endpoint = f"/type/{name_lower}"

    cached_data = await get_cache(cache_key)
    if cached_data:
        try: return TypeInfo.model_validate(cached_data)
        except Exception as e: logger.warning(f"Invalid cache for {cache_key}: {e}")

    try:
        raw_data = await fetch_resource(endpoint, client, base_url)
        # Type API directly provides id and name at root
        type_info = TypeInfo.model_validate(raw_data)
        await set_cache(cache_key, type_info.model_dump(mode='json'), ttl=cache_ttl)
        return type_info
    except ResourceNotFoundError: raise
    except Exception as e:
         logger.error(f"Error processing type '{name}': {e}", exc_info=True)
         raise PokeAPIError(f"Failed to get/process type '{name}'") from e

# --- Get List of All Generations ---
async def get_all_generations(
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL # TTL for individual items fetched
) -> List[GenerationInfo]:
    """Fetches info for all generations by getting list then details."""
    endpoint = "/generation?limit=100" # Assume limit is high enough
    try:
        list_data = await fetch_resource(endpoint, client, base_url)
        results = list_data.get('results', [])
        if not results:
             logger.warning("No generation results found from list endpoint.")
             return []

        # Fetch details concurrently using the single get_generation function
        # This leverages individual item caching
        tasks = [get_generation(gen['name'], client, base_url, cache_ttl) for gen in results]
        generation_details = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors/None and sort
        valid_generations = sorted(
            [gen for gen in generation_details if isinstance(gen, GenerationInfo)],
            key=lambda g: g.id
        )
        # Log errors encountered during gather
        for i, result in enumerate(generation_details):
             if isinstance(result, Exception):
                  logger.error(f"Failed to fetch detail for generation '{results[i].get('name')}': {result}")

        return valid_generations

    except Exception as e:
         logger.error(f"Failed to get all generations: {e}", exc_info=True)
         raise PokeAPIError("Failed to retrieve list of all generations") from e

# --- Get List of All Types ---
async def get_all_types(
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL # TTL for individual items fetched
) -> List[TypeInfo]:
    """Fetches info for all types by getting list then details."""
    endpoint = "/type?limit=100" # Assume limit high enough
    try:
        list_data = await fetch_resource(endpoint, client, base_url)
        results = list_data.get('results', [])
        if not results:
            logger.warning("No type results found from list endpoint.")
            return []

        # Fetch details concurrently using the single get_type function
        tasks = [get_type(t['name'], client, base_url, cache_ttl) for t in results]
        type_details = await asyncio.gather(*tasks, return_exceptions=True)

        valid_types = sorted(
            [t for t in type_details if isinstance(t, TypeInfo)],
            key=lambda t: t.name # Sort alphabetically
        )
        for i, result in enumerate(type_details):
             if isinstance(result, Exception):
                  logger.error(f"Failed to fetch detail for type '{results[i].get('name')}': {result}")

        return valid_types

    except Exception as e:
         logger.error(f"Failed to get all types: {e}", exc_info=True)
         raise PokeAPIError("Failed to retrieve list of all types") from e

# --- Get Evolution Chain ---
async def get_evolution_chain(
    chain_id: int,
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL,
    cache_ttl: int = DEFAULT_LIB_CACHE_TTL,
) -> EvolutionChain:
    """Fetches data for a specific Evolution Chain by ID."""
    cache_key = f"pokeapi_lib:evolution_chain:{chain_id}"
    endpoint = f"/evolution-chain/{chain_id}/"

    cached_data = await get_cache(cache_key)
    if cached_data:
        try: return EvolutionChain.model_validate(cached_data)
        except Exception as e: logger.warning(f"Invalid cache for {cache_key}: {e}")

    try:
        raw_data = await fetch_resource(endpoint, client, base_url)
        # The 'id' might be missing from the response root, add it if needed
        if 'id' not in raw_data: raw_data['id'] = chain_id
        evo_chain = EvolutionChain.model_validate(raw_data)
        await set_cache(cache_key, evo_chain.model_dump(mode='json'), ttl=cache_ttl)
        return evo_chain
    except ResourceNotFoundError: raise
    except Exception as e:
         logger.error(f"Error processing evolution chain '{chain_id}': {e}", exc_info=True)
         raise PokeAPIError(f"Failed to get/process evolution chain '{chain_id}'") from e