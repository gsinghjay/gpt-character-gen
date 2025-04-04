from fastapi import APIRouter, HTTPException, Query, Depends, Security
from typing import List, Optional
from uuid import UUID

from ...models.character import Character, CharacterCreate, ImageVariation
from ...services.image_generator import generate_character_image
from ...db.file_storage import save_character, get_character, get_all_characters, update_character, delete_character
from ...core.security import get_api_key

router = APIRouter(
    prefix="/api/characters",
    tags=["characters"],
    dependencies=[Security(get_api_key)]  # Apply API key security to all routes in this router
)

@router.post("/", response_model=Character, status_code=201)
async def create_character(character_data: CharacterCreate):
    """
    Create a new character, generate its base image, and save it.
    """
    new_character = Character(**character_data.model_dump())

    # Generate base image (can take time)
    base_image_path = await generate_character_image(new_character)
    if not base_image_path:
        # The exception should be raised in generate_character_image, but handle defensively
        raise HTTPException(status_code=500, detail="Failed to generate base image.")

    new_character.base_image_path = base_image_path
    # Note: new_character.image_seed was set in generate_character_image

    # Save character to storage
    saved_character = save_character(new_character)
    return saved_character

@router.get("/{character_id}", response_model=Character)
async def read_character_by_id(character_id: UUID):
    """
    Retrieve a specific character by its ID.
    """
    character = get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

@router.get("/", response_model=List[Character])
async def read_characters():
    """
    Retrieve a list of all characters.
    """
    return get_all_characters()

@router.post("/{character_id}/variations", response_model=Character)
async def create_character_variation(
    character_id: UUID,
    pose: Optional[str] = Query(None, description="Describe the character's pose (e.g., sitting, running)"),
    expression: Optional[str] = Query(None, description="Describe the character's expression (e.g., smiling, angry)"),
    setting: Optional[str] = Query(None, description="Describe the setting or background (e.g., forest, spaceship bridge)")
):
    """
    Generate a new image variation for an existing character based on pose, expression, or setting.
    Uses the same seed as the base image for consistent appearance.
    """
    character = get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    variation_params = {
        "pose": pose,
        "expression": expression,
        "setting": setting
    }
    # Filter out None values to pass only provided parameters
    active_variation_params = {k: v for k, v in variation_params.items() if v is not None}

    if not active_variation_params:
        raise HTTPException(status_code=400, detail="At least one variation parameter (pose, expression, setting) must be provided")

    # Generate variation image - will reuse the seed stored in character
    image_path = await generate_character_image(character, active_variation_params)
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to generate variation image.")

    # Create variation object
    variation = ImageVariation(
        image_path=image_path,
        **active_variation_params
    )

    # Add variation to character's list
    character.variations.append(variation)

    # Update the character in storage (this also updates 'updated_at')
    updated_character = update_character(character)
    if not updated_character:
         raise HTTPException(status_code=404, detail="Character not found during update process.")

    return updated_character

@router.delete("/{character_id}", status_code=204)
async def remove_character(character_id: UUID):
    """
    Delete a character and all its associated image files.
    """
    deleted = delete_character(character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Character not found")
    return None 