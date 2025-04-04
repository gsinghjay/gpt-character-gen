import json
import os
import shutil
import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException

from ..models.character import Character
from ..core.config import get_settings

# NOTE: This file-based storage is simple for MVP but has limitations:
# 1. Race Conditions: Multiple simultaneous writes can corrupt data.
# 2. Scalability: Reading/writing the entire file on each operation is inefficient.
# Consider migrating to a database (e.g., SQLite, PostgreSQL) for future versions.

logger = logging.getLogger(__name__)
settings = get_settings()
STORAGE_FILE = "characters_db.json"

def _read_storage() -> Dict[UUID, Character]:
    """Read all characters from storage file. Returns empty dict on error or if file not found."""
    if not os.path.exists(STORAGE_FILE):
        return {}
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Parse character objects, handling potential errors
            characters = {}
            for k, v in data.items():
                try:
                    characters[UUID(k)] = Character.model_validate(v)  # Use model_validate for Pydantic v2
                except Exception as parse_error:
                    logger.error(f"Failed to parse character data for key {k}: {parse_error}")
            return characters
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading storage file {STORAGE_FILE}: {e}")
        # Decide behavior: return empty / raise error / try to recover? For MVP, return empty.
        return {}

def _write_storage(characters: Dict[UUID, Character]):
    """Write characters dictionary to storage file."""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            # Use model_dump for Pydantic v2
            serialized = {str(k): v.model_dump(mode='json') for k, v in characters.items()}
            json.dump(serialized, f, indent=4)  # Added indent for readability
    except IOError as e:
        logger.error(f"Error writing to storage file {STORAGE_FILE}: {e}")
        # This is critical, maybe raise an exception?
        raise HTTPException(status_code=500, detail="Failed to save character data.")


def save_character(character: Character) -> Character:
    """Save a new or updated character to storage."""
    characters = _read_storage()
    # Ensure created_at and updated_at are set if somehow missing (should be handled by model)
    now = datetime.now()
    if not character.created_at: character.created_at = now
    character.updated_at = now  # Always set updated_at on save/update
    characters[character.id] = character
    _write_storage(characters)
    logger.info(f"Character saved/updated: {character.id}")
    return character

def get_character(character_id: UUID) -> Optional[Character]:
    """Get a character by ID."""
    characters = _read_storage()
    character = characters.get(character_id)
    if character:
        logger.info(f"Character retrieved: {character_id}")
    else:
        logger.warning(f"Character not found: {character_id}")
    return character

def get_all_characters() -> List[Character]:
    """Get all characters."""
    characters = _read_storage()
    logger.info(f"Retrieved {len(characters)} characters.")
    # Sort by creation date or name? Optional enhancement.
    return sorted(list(characters.values()), key=lambda c: c.created_at, reverse=True)


def update_character(character: Character) -> Optional[Character]:
    """Update an existing character. Returns updated character or None if not found."""
    characters = _read_storage()
    if character.id not in characters:
        logger.warning(f"Attempted to update non-existent character: {character.id}")
        return None  # Or raise HTTPException(status_code=404, ...)

    # Ensure updated_at is set on every update
    character.updated_at = datetime.now()
    characters[character.id] = character
    _write_storage(characters)
    logger.info(f"Character updated: {character.id}")
    return character

def delete_character(character_id: UUID) -> bool:
    """Delete a character and its associated image files."""
    characters = _read_storage()
    if character_id not in characters:
        logger.warning(f"Attempted to delete non-existent character: {character_id}")
        return False

    # Delete character image directory
    character_dir = os.path.join(settings.IMAGE_STORAGE_PATH, str(character_id))
    if os.path.exists(character_dir):
        try:
            shutil.rmtree(character_dir)
            logger.info(f"Deleted image directory: {character_dir}")
        except OSError as e:
            logger.error(f"Error deleting directory {character_dir}: {e}")
            # Continue to delete DB entry but log the error

    # Remove from storage dictionary
    del characters[character_id]
    _write_storage(characters)
    logger.info(f"Character deleted from storage: {character_id}")
    return True 