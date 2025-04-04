import os
import httpx
import logging
import random
from openai import OpenAI
from fastapi import HTTPException
from ..core.config import get_settings
from ..models.character import Character, ImageVariation
from datetime import datetime
from typing import Optional, Dict

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
# Ensure API key is loaded correctly
if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Add debugging to check the API key
api_key_prefix = settings.OPENAI_API_KEY[:10] if settings.OPENAI_API_KEY else "None"
logger.info(f"Using OpenAI API key with prefix: {api_key_prefix}...")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Create an async HTTP client
async_client = httpx.AsyncClient()

def create_prompt(character: Character, variation_params: Optional[Dict] = None) -> str:
    """Create a prompt for image generation based on character description and variations"""
    # Add a unique identifier to help with consistency (seed substitute)
    character_id_short = str(character.id)[:8]
    
    # Start with very explicit consistency instructions
    base_prompt = f"I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS: Character ID '{character_id_short}' - Create a portrait of this specific character: {character.description}"

    if variation_params:
        if variation_params.get("pose"):
            base_prompt += f". Pose: {variation_params['pose']}"
        if variation_params.get("expression"):
            base_prompt += f". Expression: {variation_params['expression']}"
        if variation_params.get("setting"):
            base_prompt += f". Setting: {variation_params['setting']}"

    # Add enhanced style guidance for consistency
    base_prompt += ". IMPORTANT: This MUST be exactly the same character as previous images with the same Character ID. Maintain perfect consistency in the character's core features including face, body type, hair style, clothing style, and all distinctive characteristics. Use identical art style to previous generations."

    return base_prompt

async def generate_character_image(character: Character, variation_params: Optional[Dict] = None) -> str:
    """Generate a character image using GPT-4o, download it, and save it."""
    prompt = create_prompt(character, variation_params)
    logger.info(f"Generating image for character {character.id} with prompt: {prompt[:100]}...")  # Log prompt start

    try:
        # Determine the seed to use
        if variation_params and character.image_seed is not None:
            # For variations, note the seed for reference (may or may not be used)
            seed = character.image_seed
            logger.info(f"Using seed {seed} for character variation (if supported)")
        elif not variation_params:
            # For base image, generate a new random seed
            seed = random.randint(1, 2147483647)  # Max 32-bit integer
            character.image_seed = seed
            logger.info(f"Generated new seed {seed} for base character image (if supported)")

        # Try to use the seed parameter, but fallback if not supported
        try:
            # Attempt to use the seed parameter
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                seed=seed
            )
            logger.info("Successfully used seed parameter in API call")
        except TypeError as e:
            if "unexpected keyword argument 'seed'" in str(e):
                # Seed parameter not supported in this version, use without seed
                logger.warning("Seed parameter not supported in this OpenAI client version, generating without seed")
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
            else:
                # Re-raise if it's some other TypeError
                raise

        image_url = response.data[0].url
        # Try to update the seed from the response if that field exists
        try:
            if hasattr(response.data[0], 'seed') and response.data[0].seed is not None:
                character.image_seed = response.data[0].seed
                logger.info(f"Updated seed from response: {character.image_seed}")
        except (AttributeError, IndexError) as e:
            logger.info(f"Could not access seed from response: {e}")
        
        if not image_url:
             raise HTTPException(status_code=500, detail="OpenAI did not return an image URL.")

        logger.info(f"Image generated, URL: {image_url}")

        # Download the image using httpx
        try:
            image_response = await async_client.get(image_url, timeout=60.0)
            image_response.raise_for_status()
            image_data = image_response.content
            logger.info(f"Image downloaded successfully from URL.")
        except httpx.HTTPStatusError as e:
             logger.error(f"HTTP error downloading image: {e.response.status_code} - {e.response.text}")
             raise HTTPException(status_code=500, detail=f"Failed to download image from OpenAI: Status {e.response.status_code}")
        except httpx.RequestError as e:
             logger.error(f"Request error downloading image: {e}")
             raise HTTPException(status_code=500, detail=f"Failed to download image from OpenAI: Request Error")

        # Create file path and save the image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        file_name = f"{character.id}_{timestamp}.png"

        if variation_params:
            # Store variations in a subfolder
            folder_path = os.path.join(settings.IMAGE_STORAGE_PATH, str(character.id), "variations")
        else:
            # Store base image in the character's main folder
            folder_path = os.path.join(settings.IMAGE_STORAGE_PATH, str(character.id))

        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, file_name)

        try:
            with open(file_path, "wb") as f:
                f.write(image_data)
            logger.info(f"Image saved to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save image to disk: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image file.")

        # Create relative path for storage in the model and web access
        relative_path = os.path.relpath(file_path, settings.STATIC_FILES_DIR)
        relative_path = relative_path.replace(os.sep, '/')  # Ensure web-compatible path separators

        return relative_path

    except Exception as e:
        # Catch OpenAI errors or other unexpected issues
        logger.error(f"An error occurred during image generation or processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image generation failed. Check server logs for details.") 