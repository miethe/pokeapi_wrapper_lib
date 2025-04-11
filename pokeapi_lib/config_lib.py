
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Literal, Optional

# Load environment variables from .env file if it exists
# Useful for local development
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# --- Add Constants for Base Paths ---
# Note: Ensure this matches the structure after cloning the sprites repo
POKEAPI_SPRITE_BASE_URL: str = "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
# This path MUST match how Nginx will serve it relative to its root
# Nginx root is /usr/share/nginx/html, sprites are copied to /assets/sprites
LOCAL_SPRITE_BASE_PATH: str = "/assets/sprites/"

class Settings(BaseSettings):
    """Application settings."""

    # Redis configuration
    # Reads REDIS_URL from environment or .env file
    # Default value is provided for cases where it's not set
    redis_url: str = "redis://localhost:6379/0"

    # PokeAPI base URL
    pokeapi_base_url: str = "https://pokeapi.co/api/v2"

    # Default cache TTL (Time To Live) in seconds
    # 30 days = 30 * 24 * 60 * 60 seconds
    cache_ttl_seconds: int = 30 * 24 * 60 * 60 # Default: 30 days

    # Max Pokemon ID to fetch for summary (adjust as new generations are added)
    # Gen 9 ends at 1025 (as of early 2024), let's add some buffer
    max_pokemon_id_to_fetch: int = 1025 # Example: covers up to Paldean Pokémon + some buffer

    # --- Sprite Setting ---
    # Use 'local' to serve from /assets/sprites, 'remote' to use PokeAPI URLs
    sprite_source_mode: Literal['local', 'remote'] = "local" # Default to local

    class Config:
        # Specifies the .env file encoding
        env_file_encoding = 'utf-8'
        # If you use a different name for your .env file, specify it here
        # env_file = '.env'


# Create a single instance of the settings to be imported in other modules
settings = Settings()

# Example usage (optional, for testing):
if __name__ == "__main__":
    print(f"Redis URL: {settings.redis_url}")
    print(f"PokeAPI Base URL: {settings.pokeapi_base_url}")
    print(f"Default Cache TTL: {settings.cache_ttl_seconds} seconds")
    print(f"Max Pokemon ID: {settings.max_pokemon_id_to_fetch}")