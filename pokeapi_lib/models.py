# pokeapi_lib/models.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any
import logging

from .config_lib import settings, POKEAPI_SPRITE_BASE_URL, LOCAL_SPRITE_BASE_PATH # Use library-specific config if needed

logger = logging.getLogger(__name__)

# --- Basic Named Resources ---
class NamedAPIResource(BaseModel):
    name: str
    url: str

# --- Type Models ---
class TypeInfo(BaseModel):
    """Basic info about a Type resource from PokeAPI."""
    name: str
    # ID isn't directly available in all contexts, fetch separately if needed
    id: Optional[int] = None # Make ID optional or fetch in get_type

class PokemonTypeSlot(BaseModel):
    slot: int
    type: NamedAPIResource # Use NamedAPIResource here

# --- Ability Models ---
class PokemonAbilitySlot(BaseModel):
    slot: int
    is_hidden: bool
    ability: NamedAPIResource # Use NamedAPIResource

# --- Stat Models ---
class PokemonStatData(BaseModel):
    stat: NamedAPIResource # Use NamedAPIResource
    base_stat: int
    effort: int

# --- Sprite Models (Handles transformation) ---
class SpriteData(BaseModel):
    front_default: Optional[str] = None
    back_default: Optional[str] = None
    front_shiny: Optional[str] = None
    back_shiny: Optional[str] = None
    front_female: Optional[str] = None
    back_female: Optional[str] = None
    front_shiny_female: Optional[str] = None
    back_shiny_female: Optional[str] = None
    
    # Official Artwork (extracted via validator)
    official_artwork: Optional[str] = Field(None, description="URL for official artwork sprite")

    # Animated Sprites (will be populated by root_validator)
    animated_front_default: Optional[str] = None
    animated_back_default: Optional[str] = None
    animated_front_shiny: Optional[str] = None
    animated_back_shiny: Optional[str] = None
    
    # Use aliases for nested fields (requires populate_by_name=True)
    #official_artwork_front: Optional[str] = Field(None, validation_alias='other.official-artwork.front_default')
    #animated_front_default: Optional[str] = Field(None, validation_alias='versions.generation-v.black-white.animated.front_default')
    #animated_front_shiny: Optional[str] = Field(None, validation_alias='versions.generation-v.black-white.animated.front_shiny')
    # Add aliases for other animated/nested sprites if needed

    @root_validator(pre=True)
    def extract_nested_sprites(cls, values: dict):
        """
        Extracts deeply nested sprites (official artwork, animated)
        and adds them to the top level for easier field assignment.
        Runs before individual field validation.
        """
        if not isinstance(values, dict): # Handle case where input isn't a dict
            return values

        # Extract Official Artwork
        official_artwork_url = values.get('other', {}).get('official-artwork', {}).get('front_default')
        if official_artwork_url:
            values['official_artwork'] = official_artwork_url # Add to dict for field assignment

        # Extract Animated Sprites (Gen V Black/White)
        try:
            animated_sprites = values.get('versions', {}).get('generation-v', {}).get('black-white', {}).get('animated', {})
            if animated_sprites: # Check if animated dict exists and is not None
                 values['animated_front_default'] = animated_sprites.get('front_default')
                 values['animated_back_default'] = animated_sprites.get('back_default')
                 values['animated_front_shiny'] = animated_sprites.get('front_shiny')
                 values['animated_back_shiny'] = animated_sprites.get('back_shiny')
                 values['animated_front_female'] = animated_sprites.get('front_female') # Get if exists
                 values['animated_back_female'] = animated_sprites.get('back_female')
                 values['animated_front_shiny_female'] = animated_sprites.get('front_shiny_female')
                 values['animated_back_shiny_female'] = animated_sprites.get('back_shiny_female')
        except Exception as e:
            # Log potential errors during complex extraction, but don't fail validation
            logger.warning(f"Could not extract animated sprites: {e}", exc_info=False) # Set exc_info=False to avoid clutter

        return values

    @validator("*", pre=True, allow_reuse=True)
    def ensure_https_url(cls, value):
        """Ensure sprite URLs are HTTPS for security and browser compatibility."""
        if isinstance(value, str) and value.startswith("http://"):
            return value.replace("http://", "https://", 1) # Replace only the first occurrence
        return value

    # --- Root validator ONLY for URL Transformation ---
    @root_validator(skip_on_failure=True) # Post-validation default
    def transform_urls_if_local(cls, values: Dict[str, Any]):
        # Assuming 'settings' is accessible here or passed via context
        # Replace with actual config access method
        try:
             from .config_lib import settings, POKEAPI_SPRITE_BASE_URL, LOCAL_SPRITE_BASE_PATH
             _sprite_source_mode = settings.sprite_source_mode
             _local_base = LOCAL_SPRITE_BASE_PATH
             _remote_base = POKEAPI_SPRITE_BASE_URL
        except ImportError: # Fallback if config system isn't set up yet
             logger.warning("Sprite config not found, defaulting to remote.")
             _sprite_source_mode = 'remote'

        if _sprite_source_mode == 'local':
            logger.debug(f"LIB: Transforming sprite URLs to local. Base: {_local_base}")
            for key, url in values.items():
                if isinstance(url, str) and url.startswith(_remote_base):
                    # Replace base URL with local path base
                    # Example: https://.../master/sprites/pokemon/1.png -> /assets/sprites/sprites/pokemon/1.png
                    relative_path = url.removeprefix(_remote_base)
                    values[key] = f"{_local_base}{relative_path}"
                elif isinstance(url, str) and not url.startswith(('/', 'http')):
                     # Handle cases where a relative path might already exist unexpectedly? Optional.
                     logger.warning(f"Sprite URL '{url}' for key '{key}' is not absolute. Skipping transformation.")
                elif isinstance(url, str) and url.startswith("http://"): # Ensure HTTPS for remote
                     values[key] = url.replace("http://", "https://", 1)
        elif _sprite_source_mode == 'remote': # Ensure HTTPS for remote mode too
             for key, url in values.items():
                  if isinstance(url, str) and url.startswith("http://"):
                     values[key] = url.replace("http://", "https://", 1)

        return values

    class Config:
        #populate_by_name = True # Enable alias usage
        pass

class BasePokemon(BaseModel):
    """Core Pokemon data returned by the library."""
    id: int
    name: str
    height: int
    weight: int
    base_experience: Optional[int] = None
    order: int
    is_default: bool
    location_area_encounters: str # URL
    types: List[PokemonTypeSlot]
    abilities: List[PokemonAbilitySlot]
    stats: List[PokemonStatData]
    sprites: SpriteData # Uses the enhanced SpriteData
    species: NamedAPIResource # Keep simple resource link

    class Config:
        populate_by_name = True

# --- Species Model (Add more fields) ---
class FlavorText(BaseModel):
    flavor_text: str
    language: NamedAPIResource
    version: NamedAPIResource

class Genus(BaseModel):
    genus: str
    language: NamedAPIResource

class BaseSpecies(BaseModel):
     """Core Species data returned by the library."""
     id: int
     name: str
     order: int
     gender_rate: int
     capture_rate: int
     base_happiness: Optional[int] = None
     is_baby: bool
     is_legendary: bool
     is_mythical: bool
     hatch_counter: Optional[int] = None
     generation: NamedAPIResource
     evolves_from_species: Optional[NamedAPIResource] = None
     evolution_chain: Dict[str, str] # Contains 'url' key
     egg_groups: List[NamedAPIResource] = []
     flavor_text_entries: List[FlavorText] = []
     genera: List[Genus] = []
     habitat: Optional[NamedAPIResource] = None
     shape: Optional[NamedAPIResource] = None
     growth_rate: Optional[NamedAPIResource] = None

     class Config:
         populate_by_name = True

# --- Generation Model ---
class GenerationInfo(BaseModel):
    """Represents basic info about a Pokemon Generation."""
    id: int
    name: str # e.g., generation-i
    region_name: str # e.g., kanto

# --- Evolution Chain Models ---
class EvolutionDetail(BaseModel):
    # Simplified, add more fields as needed (trigger, item, conditions etc.)
    min_level: Optional[int] = None
    trigger: NamedAPIResource
    item: Optional[NamedAPIResource] = None
    # Add other common fields: known_move, time_of_day, relative_physical_stats etc.

class ChainLink(BaseModel):
    species: NamedAPIResource
    evolves_to: List['ChainLink'] = [] # Recursive definition
    evolution_details: List[EvolutionDetail] = []

class EvolutionChain(BaseModel):
    id: int
    chain: ChainLink
    baby_trigger_item: Optional[NamedAPIResource] = None