**Project Goal:** Create a Minimum Viable Product (MVP) web application using FastAPI and OpenAI's GPT-4o to generate consistent base portraits of fictional characters from descriptions and allow creating variations (pose, expression, setting).

**Key Updates Incorporated:**

1.  **Correct Image Downloading:** Uses `httpx` to fetch images from OpenAI URLs.
2.  **Secure API Key Handling:** Moves the hardcoded API key to configuration (`.env`).
3.  **API Key Enforcement:** Applies the API key security dependency to the API router.
4.  **`updated_at` Timestamp:** Automatically updates the timestamp when modifying characters.
5.  **Dependency Pinning:** Uses `==` in `requirements.txt`.
6.  **Improved Relative Paths:** More robust relative path calculation for images.
7.  **Basic Error Logging:** Added print statements (placeholder for proper logging) in image generation.
8.  **Documentation:** Updated README with `.env` changes, API key info, and limitations.

---

**Updated Project Plan:**

**1. Project Structure (Unchanged)**

```
fictional_character_creator/
├── app/
│   ├── main.py             # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       └── characters.py  # Character-related endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Configuration (API keys, etc.)
│   │   └── security.py     # Basic API security
│   ├── db/
│   │   ├── __init__.py
│   │   └── file_storage.py # Simple file-based storage (MVP limitation)
│   ├── models/
│   │   ├── __init__.py
│   │   └── character.py    # Character data models
│   └── services/
│       ├── __init__.py
│       └── image_generator.py  # GPT-4o integration
├── static/
│   ├── css/
│   ├── js/
│   └── images/             # Store generated images
├── templates/
│   └── index.html          # Simple UI for the MVP
├── requirements.txt
├── README.md
└── .env                    # Store secrets like API keys (add to .gitignore)
```

**2. `app/core/config.py`**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    APP_NAME: str = "Fictional Character Creator"
    OPENAI_API_KEY: str
    STATIC_FILES_DIR: str = "static"
    IMAGE_STORAGE_PATH: str = os.path.join(STATIC_FILES_DIR, "images")
    # ADDED: API Key for application security
    API_KEY: str = "default-secret-key-please-change" # Provide a default or make mandatory without default

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8' # ADDED: Explicit encoding

@lru_cache()
def get_settings():
    # Ensure IMAGE_STORAGE_PATH exists when settings are loaded
    settings = Settings()
    os.makedirs(settings.IMAGE_STORAGE_PATH, exist_ok=True)
    return settings

```

**3. `app/models/character.py` (Unchanged from original)**

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

class CharacterBase(BaseModel):
    description: str
    name: Optional[str] = None

class CharacterCreate(CharacterBase):
    pass

class ImageVariation(BaseModel):
    image_path: str
    pose: Optional[str] = None
    expression: Optional[str] = None
    setting: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

class Character(CharacterBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now) # Timestamp for updates
    base_image_path: Optional[str] = None
    variations: List[ImageVariation] = []
```

**4. `app/services/image_generator.py`**

```python
import os
import httpx # ADDED: HTTP client for downloading images
import logging # ADDED: Basic logging setup
from openai import OpenAI
from fastapi import HTTPException
from ..core.config import get_settings
from ..models.character import Character, ImageVariation
from datetime import datetime

# ADDED: Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
# Ensure API key is loaded correctly
if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Create an async HTTP client (recommended for FastAPI)
# Reuse the client for efficiency
async_client = httpx.AsyncClient()

def create_prompt(character: Character, variation_params: Optional[dict] = None) -> str:
    """Create a prompt for GPT-4o image generation based on character description and variations"""
    base_prompt = f"Create a high-quality character portrait of the following character: {character.description}"

    if variation_params:
        if variation_params.get("pose"):
            base_prompt += f". Pose: {variation_params['pose']}"
        if variation_params.get("expression"):
            base_prompt += f". Expression: {variation_params['expression']}"
        if variation_params.get("setting"):
            base_prompt += f". Setting: {variation_params['setting']}"

    # Add style guidance for consistency
    base_prompt += ". Maintain a consistent appearance for this character's core features like face, body type, and distinctive characteristics. Use a consistent art style (e.g., realistic painting, anime, cartoon) with clear details."

    return base_prompt

async def generate_character_image(character: Character, variation_params: Optional[dict] = None) -> str:
    """Generate a character image using GPT-4o, download it, and save it."""
    prompt = create_prompt(character, variation_params)
    logger.info(f"Generating image for character {character.id} with prompt: {prompt[:100]}...") # Log prompt start

    try:
        # Generate image using OpenAI API
        response = await client.images.generate( # CHANGED: use await for async client if available (standard client is sync)
            model="dall-e-3", # CHANGED: Suggest using DALL-E 3 as gpt-4o is primarily text/vision. If gpt-4o image gen is specifically desired, keep gpt-4o. DALL-E 3 often better for pure generation.
            prompt=prompt,
            size="1024x1024",
            quality="standard", # Use "hd" for potentially better quality, higher cost
            n=1,
            # style="vivid", # Optional: 'vivid' or 'natural' for DALL-E 3
        )

        image_url = response.data[0].url
        if not image_url:
             raise HTTPException(status_code=500, detail="OpenAI did not return an image URL.")

        logger.info(f"Image generated, URL: {image_url}")

        # Download the image using httpx
        # CHANGED: Correct image download logic
        try:
            async with async_client as client: # Use the shared async client
                image_response = await client.get(image_url, timeout=60.0) # ADDED: Timeout
                image_response.raise_for_status() # Raise exception for bad status codes (4xx, 5xx)
                image_data = image_response.content
            logger.info(f"Image downloaded successfully from URL.")
        except httpx.HTTPStatusError as e:
             logger.error(f"HTTP error downloading image: {e.response.status_code} - {e.response.text}")
             raise HTTPException(status_code=500, detail=f"Failed to download image from OpenAI: Status {e.response.status_code}")
        except httpx.RequestError as e:
             logger.error(f"Request error downloading image: {e}")
             raise HTTPException(status_code=500, detail=f"Failed to download image from OpenAI: Request Error")


        # Create file path and save the image
        # ADDED: Microseconds for better uniqueness if generated quickly
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

        # Saving the file is synchronous I/O - potentially blocking
        # For MVP, this is acceptable. For production, use aiofiles or run_in_threadpool
        try:
            with open(file_path, "wb") as f:
                f.write(image_data)
            logger.info(f"Image saved to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save image to disk: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image file.")

        # Create relative path for storage in the model and web access
        # CHANGED: Use os.path.relpath and ensure forward slashes
        relative_path = os.path.relpath(file_path, settings.STATIC_FILES_DIR)
        relative_path = relative_path.replace(os.sep, '/') # Ensure web-compatible path separators

        return relative_path

    except Exception as e:
        # Catch OpenAI errors or other unexpected issues
        logger.error(f"An error occurred during image generation or processing: {e}", exc_info=True) # Log stack trace
        # Avoid leaking potentially sensitive details from underlying exceptions like OpenAI errors
        raise HTTPException(status_code=500, detail=f"Image generation failed. Check server logs for details.")

```

**5. `app/db/file_storage.py`**

```python
import json
import os
import shutil
import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime # ADDED: Import datetime
from fastapi import HTTPException # ADDED: For potential errors

from ..models.character import Character
from ..core.config import get_settings

# NOTE: This file-based storage is simple for MVP but has limitations:
# 1. Race Conditions: Multiple simultaneous writes can corrupt data.
# 2. Scalability: Reading/writing the entire file on each operation is inefficient.
# Consider migrating to a database (e.g., SQLite, PostgreSQL) for future versions.

logger = logging.getLogger(__name__)
settings = get_settings()
STORAGE_FILE = "characters_db.json" # Renamed for clarity

# Basic file lock mechanism (very rudimentary, not robust across processes/machines)
# A proper library like 'filelock' would be better if sticking with files temporarily.
# For MVP, we'll skip locking but acknowledge the risk.

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
                    characters[UUID(k)] = Character.model_validate(v) # Use model_validate for Pydantic v2
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
            json.dump(serialized, f, indent=4) # Added indent for readability
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
    character.updated_at = now # Always set updated_at on save/update
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
        return None # Or raise HTTPException(status_code=404, ...)

    # CHANGED: Ensure updated_at is set on every update
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

```

**6. `app/api/endpoints/characters.py`**

```python
from fastapi import APIRouter, HTTPException, Query, Depends, Security # ADDED: Depends, Security
from typing import List, Optional
from uuid import UUID

from ...models.character import Character, CharacterCreate, ImageVariation
from ...services.image_generator import generate_character_image
from ...db.file_storage import save_character, get_character, get_all_characters, update_character, delete_character # ADDED: delete_character import
from ...core.security import get_api_key # ADDED: Import security function

# CHANGED: Apply API key security to all routes in this router
router = APIRouter(
    prefix="/api/characters",
    tags=["characters"],
    dependencies=[Security(get_api_key)]
)

@router.post("/", response_model=Character, status_code=201) # ADDED: status_code 201 for creation
async def create_character(character_data: CharacterCreate):
    """
    Create a new character, generate its base image, and save it.
    """
    new_character = Character(**character_data.model_dump()) # Use model_dump for Pydantic v2

    # Generate base image (can take time)
    base_image_path = await generate_character_image(new_character)
    if not base_image_path:
        # The exception should be raised in generate_character_image, but handle defensively
        raise HTTPException(status_code=500, detail="Failed to generate base image.")

    new_character.base_image_path = base_image_path

    # Save character to storage
    saved_character = save_character(new_character) # save_character now also handles update_at
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
    return get_all_characters() # Already sorted by creation date in file_storage

@router.post("/{character_id}/variations", response_model=Character)
async def create_character_variation(
    character_id: UUID,
    pose: Optional[str] = Query(None, description="Describe the character's pose (e.g., sitting, running)"),
    expression: Optional[str] = Query(None, description="Describe the character's expression (e.g., smiling, angry)"),
    setting: Optional[str] = Query(None, description="Describe the setting or background (e.g., forest, spaceship bridge)")
):
    """
    Generate a new image variation for an existing character based on pose, expression, or setting.
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

    # Generate variation image
    image_path = await generate_character_image(character, active_variation_params)
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to generate variation image.")

    # Create variation object
    variation = ImageVariation(
        image_path=image_path,
        **active_variation_params # Pass only the active parameters
    )

    # Add variation to character's list
    character.variations.append(variation)

    # Update the character in storage (this also updates 'updated_at')
    updated_character = update_character(character)
    if not updated_character:
         # Should not happen if get_character succeeded, but handle defensively
         raise HTTPException(status_code=404, detail="Character not found during update process.")

    return updated_character

# ADDED: Endpoint to delete a character
@router.delete("/{character_id}", status_code=204) # 204 No Content is standard for successful DELETE
async def remove_character(character_id: UUID):
    """
    Delete a character and all its associated image files.
    """
    deleted = delete_character(character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Character not found")
    # No response body needed for 204
    return None

```

**7. `app/main.py` (Minor adjustments)**

```python
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware # ADDED: For potential CORS issues if frontend served differently

from .core.config import get_settings
from .api.endpoints import characters # Ensure API endpoints are imported

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version="0.1.0") # ADDED: Version

# ADDED: CORS Middleware (useful if frontend/API domains differ)
# Adjust origins as needed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins for simplicity in MVP - RESTRICT THIS IN PRODUCTION
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# Mount static files (CSS, JS, Images)
# Ensure the directory exists
static_dir = settings.STATIC_FILES_DIR
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    os.makedirs(os.path.join(static_dir, "images"), exist_ok=True) # Ensure images subdir exists too
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Templates
templates = Jinja2Templates(directory="templates")

# Include API routers
# Note: Security dependency is applied within the router itself now
app.include_router(characters.router)

@app.get("/", include_in_schema=False) # Hide from OpenAPI docs
async def root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

# Example of a health check endpoint (good practice)
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

```

**8. `app/core/security.py`**

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader # CHANGED: Use APIKeyHeader
from ..core.config import get_settings

settings = get_settings()

API_KEY_NAME = "X-API-Key" # Standard header name
api_key_header_auth = APIKeyHeader(name=API_KEY_NAME, auto_error=False) # Set auto_error=False to handle error manually

async def get_api_key(api_key_header: str = Security(api_key_header_auth)):
    """Retrieve and validate API key from the X-API-Key header."""
    # CHANGED: Get the correct API key from settings
    correct_api_key = settings.API_KEY
    if not correct_api_key:
        # Should not happen if config is loaded, but safety check
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key not configured on server.",
        )

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key in X-API-Key header",
        )

    if api_key_header != correct_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    # If valid, just return the key (or True, or None - doesn't strictly matter what's returned here)
    return api_key_header

```

**9. `__init__.py` Files (Ensure they exist as before)**

Create empty `__init__.py` files in `app/api/`, `app/api/endpoints/`, `app/core/`, `app/db/`, `app/models/`, `app/services/` to make them Python packages.

**10. `requirements.txt`**

```
# Framework
fastapi==0.111.0  # CHANGED: Pinned version
uvicorn[standard]==0.29.0 # CHANGED: Pinned version, include 'standard' for websockets/watchfiles if needed later

# Configuration & Data Validation
pydantic==2.7.1 # CHANGED: Pinned version
pydantic-settings==2.2.1 # CHANGED: Pinned version
python-dotenv==1.0.1 # CHANGED: Pinned version

# OpenAI API
openai==1.28.0 # CHANGED: Pinned version

# HTTP Client (for image download)
httpx==0.27.0 # ADDED: Pinned version

# Form Data / File Uploads (FastAPI dependency)
python-multipart==0.0.9 # CHANGED: Pinned version

# Templating Engine
Jinja2==3.1.4 # CHANGED: Pinned version

# Logging (Standard Library, but good to note)
# logging

# Optional: For improved file storage (if not using DB yet)
# filelock==3.13.1

# Optional: For async file I/O (if needed later)
# aiofiles==23.2.1
```

**11. `README.md`**

```markdown
# Fictional Character Creator MVP

An application that generates consistent character portraits from written descriptions using OpenAI (DALL-E 3 / GPT-4o), allowing for variations in poses, expressions, and settings.

## Features

- Create fictional characters with detailed descriptions and optional names.
- Generate a base character portrait using OpenAI's image generation API.
- Create variations of the base character with different poses, expressions, and settings, aiming for consistency.
- Simple web interface (HTML, JS, Bootstrap) for interacting with the application.
- Basic API key security (`X-API-Key` header).
- Simple file-based JSON storage for character data (MVP limitation).
- Generated images stored locally in the `static/images` directory.

## Technology Stack

- Backend: FastAPI (Python)
- Image Generation: OpenAI API (DALL-E 3 recommended)
- HTTP Client: HTTPX
- Storage: Simple file-based JSON storage (`characters_db.json`)
- Frontend: HTML, JavaScript (vanilla), Bootstrap 5
- Configuration: Pydantic Settings, `.env` file

## Setup Instructions

1.  **Clone Repository:**
    ```bash
    git clone <your-repo-url>
    cd fictional-character-creator
    ```
2.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create `.env` File:**
    Create a file named `.env` in the root directory (`fictional_character_creator/`) and add your secrets:
    ```dotenv
    OPENAI_API_KEY="your_openai_api_key_here"
    # This key secures your API endpoints. Use a strong, random string.
    API_KEY="your_chosen_secret_api_key_for_this_app"
    ```
    *Note: Add `.env` to your `.gitignore` file to avoid committing secrets.*

5.  **Run the Application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The `--reload` flag automatically restarts the server when code changes.

6.  **Access the Application:**
    Open your browser and navigate to `http://127.0.0.1:8000`.

## API Usage

The API endpoints are protected by the API key specified in your `.env` file. When making requests to `/api/*` endpoints (e.g., using `curl`, Postman, or your frontend), you must include the `X-API-Key` header:

```
X-API-Key: your_chosen_secret_api_key_for_this_app
```

## Project Structure

(Include the structure diagram from the original prompt here)

## Known Limitations & Future Improvements (MVP Scope)

*   **Storage:** The current `file_storage.py` uses a single JSON file. This is **not suitable for production** due to potential race conditions during concurrent writes and poor performance with many characters. **Next Step:** Migrate to a database (e.g., SQLite for simplicity, PostgreSQL for scalability) using an ORM like SQLAlchemy or SQLModel.
*   **Error Handling:** Error handling is basic. More robust logging and potentially custom exception handlers could be added.
*   **Image Generation Consistency:** While the prompt attempts to enforce consistency, AI image generation can still produce variations in appearance. Advanced techniques (e.g., image-to-image with masks, fine-tuning if possible, more complex prompt engineering) might be needed for higher consistency.
*   **Frontend Feedback:** The frontend provides basic loading states but could be improved with visual spinners or progress indicators for long operations like image generation. Error messages could be displayed more gracefully within the UI instead of using `alert()`.
*   **Asynchronous Operations:** File I/O in `file_storage.py` is currently synchronous. For better performance under load, consider using `aiofiles` or running synchronous operations in a thread pool (`fastapi.concurrency.run_in_threadpool`). This is less critical if migrating to an async database driver.
*   **Testing:** No automated tests are included in the MVP. Adding unit and integration tests is crucial for maintainability.

```

**12. `templates/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fictional Character Creator</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        /* (Styles from original - unchanged) */
        .character-card { margin-bottom: 20px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .character-image { width: 100%; height: 300px; object-fit: cover; background-color: #eee; /* Placeholder color */ }
        .variation-image { width: 100%; height: 200px; object-fit: cover; border-radius: 5px; background-color: #eee; }
        .loading-overlay { /* Basic loading indicator */
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(255, 255, 255, 0.7); display: flex;
            align-items: center; justify-content: center; z-index: 10;
        }
        .card .loading-overlay { border-radius: 10px; } /* Adjust for card radius */
        .modal-content .loading-overlay { border-radius: var(--bs-modal-border-radius); }
    </style>
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">Fictional Character Creator</h1>

        <!-- ADDED: API Key Input (Simple approach for MVP testing) -->
        <div class="alert alert-info">
            <strong>Note:</strong> Enter the API Key defined in your <code>.env</code> file below to interact with the API.
            <input type="password" id="apiKeyInput" class="form-control mt-2" placeholder="Enter X-API-Key">
        </div>

        <!-- Character Creation Form -->
        <div class="card mb-5" id="createCharacterCard">
            <div class="card-header">
                <h3>Create New Character</h3>
            </div>
            <div class="card-body position-relative"> <!-- ADDED: position-relative for overlay -->
                 <!-- ADDED: Loading Overlay -->
                <div class="loading-overlay d-none" id="createLoadingOverlay">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                <form id="characterForm">
                    <!-- (Form fields unchanged) -->
                     <div class="mb-3">
                        <label for="characterName" class="form-label">Character Name (Optional)</label>
                        <input type="text" class="form-control" id="characterName">
                    </div>
                    <div class="mb-3">
                        <label for="characterDescription" class="form-label">Character Description</label>
                        <textarea class="form-control" id="characterDescription" rows="4" placeholder="Describe your character in detail (appearance, clothing, distinctive features, etc.)" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Create Character</button>
                </form>
                 <div id="createErrorAlert" class="alert alert-danger mt-3 d-none" role="alert"></div> <!-- ADDED: Error display -->
            </div>
        </div>

        <!-- Character Gallery -->
        <h3 class="mb-3">Your Characters</h3>
        <div id="characterGallery" class="row">
            <!-- Characters will be loaded here dynamically -->
            <div class="col-12 text-center" id="noCharactersMessage">
                <p>Loading characters or none created yet...</p>
            </div>
        </div>
        <div id="galleryErrorAlert" class="alert alert-danger mt-3 d-none" role="alert"></div> <!-- ADDED: Error display -->


        <!-- Character Detail Modal -->
        <div class="modal fade" id="characterDetailModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="characterModalTitle">Character Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body position-relative"> <!-- ADDED: position-relative for overlay -->
                        <!-- ADDED: Loading Overlay for Modal -->
                        <div class="loading-overlay d-none" id="variationLoadingOverlay">
                             <div class="spinner-border text-primary" role="status">
                                 <span class="visually-hidden">Generating Variation...</span>
                             </div>
                         </div>

                        <div class="row mb-4">
                            <!-- (Modal content structure unchanged) -->
                             <div class="col-md-6">
                                <img id="characterModalImage" src="" alt="Character" class="img-fluid rounded character-image">
                            </div>
                            <div class="col-md-6">
                                <h4 id="characterModalName">Character Name</h4>
                                <p id="characterModalDescription" style="white-space: pre-wrap;"></p> <!-- ADDED: Preserve whitespace -->
                                <small class="text-muted" id="characterModalId"></small><br> <!-- Show ID -->
                                <small class="text-muted" id="characterModalDates"></small> <!-- Show dates -->
                                <!-- ADDED: Delete button -->
                                <button id="deleteCharacterBtn" class="btn btn-danger btn-sm mt-3">Delete Character</button>
                            </div>
                        </div>

                        <h5>Create a Variation</h5>
                        <form id="variationForm" class="mb-4">
                            <input type="hidden" id="characterIdForVariation">
                             <!-- (Variation form fields unchanged) -->
                             <div class="row">
                                <div class="col-md-4 mb-2">
                                    <input type="text" class="form-control" id="poseInput" placeholder="Pose (e.g., sitting, running)">
                                </div>
                                <div class="col-md-4 mb-2">
                                    <input type="text" class="form-control" id="expressionInput" placeholder="Expression (e.g., smiling, angry)">
                                </div>
                                <div class="col-md-4 mb-2">
                                    <input type="text" class="form-control" id="settingInput" placeholder="Setting (e.g., forest, beach)">
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">Generate Variation</button>
                        </form>
                         <div id="variationErrorAlert" class="alert alert-danger mt-3 d-none" role="alert"></div> <!-- ADDED: Error display -->


                        <h5>Variations</h5>
                        <div id="variationsGallery" class="row">
                            <!-- Variations will be loaded here dynamically -->
                            <div class="col-12 text-center" id="noVariationsMessage">
                                <p>No variations yet. Create one using the form above!</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // --- Configuration ---
        const API_BASE_URL = '/api'; // Use relative path

        // --- DOM Elements ---
        const characterForm = document.getElementById('characterForm');
        const characterGallery = document.getElementById('characterGallery');
        const noCharactersMessage = document.getElementById('noCharactersMessage');
        const characterDetailModalEl = document.getElementById('characterDetailModal');
        const characterDetailModal = new bootstrap.Modal(characterDetailModalEl);
        const variationForm = document.getElementById('variationForm');
        const variationsGallery = document.getElementById('variationsGallery');
        const noVariationsMessage = document.getElementById('noVariationsMessage');
        const apiKeyInput = document.getElementById('apiKeyInput'); // ADDED
        const createLoadingOverlay = document.getElementById('createLoadingOverlay'); // ADDED
        const variationLoadingOverlay = document.getElementById('variationLoadingOverlay'); // ADDED
        const createErrorAlert = document.getElementById('createErrorAlert'); // ADDED
        const galleryErrorAlert = document.getElementById('galleryErrorAlert'); // ADDED
        const variationErrorAlert = document.getElementById('variationErrorAlert'); // ADDED
        const deleteCharacterBtn = document.getElementById('deleteCharacterBtn'); // ADDED

        // --- State ---
        let currentCharacterId = null; // Store ID of character being viewed/deleted

        // --- Utility Functions ---
        // ADDED: Function to get API Key from input
        function getApiKey() {
            const key = apiKeyInput.value.trim();
            if (!key) {
                alert('Please enter your API Key.');
                apiKeyInput.focus();
                return null;
            }
            return key;
        }

        // ADDED: Helper for fetch requests with API key and error handling
        async function apiFetch(url, options = {}) {
            const apiKey = getApiKey();
            if (!apiKey) return null; // Stop if no key provided

            const headers = {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey, // Include API key
                ...(options.headers || {}),
            };

            try {
                const response = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });

                if (!response.ok) {
                    let errorDetail = `HTTP error! Status: ${response.status}`;
                    try {
                        const errorData = await response.json();
                        errorDetail = errorData.detail || JSON.stringify(errorData);
                    } catch (jsonError) {
                        // If response is not JSON, use text
                        try {
                           errorDetail = await response.text();
                        } catch (textError) {
                           // Keep the original status code error
                        }
                    }
                    console.error('API Error Response:', errorDetail); // Log detailed error
                    throw new Error(errorDetail); // Throw error with detail
                }

                // Handle 204 No Content (for DELETE)
                 if (response.status === 204) {
                     return null; // Or return a specific success indicator if needed
                 }

                return await response.json();
            } catch (error) {
                console.error('API Fetch Error:', error);
                 // Return the error object to be handled by the caller
                 return { error: error.message || 'An unexpected error occurred.' };
            }
        }

        // ADDED: Functions to show/hide loading overlays
        function showLoading(overlayElement) { overlayElement.classList.remove('d-none'); }
        function hideLoading(overlayElement) { overlayElement.classList.add('d-none'); }

        // ADDED: Function to display errors
        function showError(alertElement, message) {
            alertElement.textContent = message;
            alertElement.classList.remove('d-none');
        }
        function hideError(alertElement) {
            alertElement.textContent = '';
            alertElement.classList.add('d-none');
        }

        // --- API Functions ---
        async function fetchCharacters() {
            hideError(galleryErrorAlert); // Clear previous errors
            const result = await apiFetch('/characters');
            if (result && result.error) {
                showError(galleryErrorAlert, `Failed to load characters: ${result.error}`);
                return [];
            }
            return result || []; // Return empty array if fetch failed slightly differently
        }

        async function createCharacter(characterData) {
            showLoading(createLoadingOverlay);
            hideError(createErrorAlert);
            const result = await apiFetch('/characters', {
                method: 'POST',
                body: JSON.stringify(characterData),
            });
            hideLoading(createLoadingOverlay);
            if (result && result.error) {
                 showError(createErrorAlert, `Failed to create character: ${result.error}`);
                 return null;
            }
            return result;
        }

        async function createVariation(characterId, variationData) {
             showLoading(variationLoadingOverlay);
             hideError(variationErrorAlert);
            const params = new URLSearchParams();
            if (variationData.pose) params.append('pose', variationData.pose);
            if (variationData.expression) params.append('expression', variationData.expression);
            if (variationData.setting) params.append('setting', variationData.setting);

            const result = await apiFetch(`/characters/${characterId}/variations?${params.toString()}`, {
                method: 'POST',
            });
             hideLoading(variationLoadingOverlay);
             if (result && result.error) {
                 showError(variationErrorAlert, `Failed to create variation: ${result.error}`);
                 return null;
             }
            return result;
        }

        // ADDED: API function for delete
        async function deleteCharacter(characterId) {
             showLoading(variationLoadingOverlay); // Reuse modal overlay
             hideError(variationErrorAlert); // Reuse modal error display

             const result = await apiFetch(`/characters/${characterId}`, {
                 method: 'DELETE',
             });

             hideLoading(variationLoadingOverlay);
             if (result && result.error) {
                 showError(variationErrorAlert, `Failed to delete character: ${result.error}`);
                 return false; // Indicate failure
             }
             // If successful, result will be null (due to 204 handling in apiFetch)
             return true; // Indicate success
         }


        // --- UI Functions ---
        function renderCharacterCard(character) {
            const card = document.createElement('div');
            card.className = 'col-md-4';
            // CHANGED: Use static path correctly, handle missing image
             const imagePath = character.base_image_path ? `/static/${character.base_image_path}` : '/static/images/placeholder.png'; // Assume placeholder exists
            card.innerHTML = `
                <div class="character-card card">
                    <img src="${imagePath}" class="character-image card-img-top" alt="${character.name || 'Character'}" loading="lazy">
                    <div class="card-body p-3">
                        <h5 class="card-title">${character.name || 'Unnamed Character'}</h5>
                        <p class="card-text small">${character.description.substring(0, 100)}${character.description.length > 100 ? '...' : ''}</p>
                        <button class="btn btn-sm btn-outline-primary view-character" data-character-id="${character.id}">View Details</button>
                    </div>
                </div>
            `;

            card.querySelector('.view-character').addEventListener('click', async () => {
                 // Fetch full details when opening modal to ensure latest data
                 hideError(variationErrorAlert); // Clear modal errors
                 const fullCharacterData = await apiFetch(`/characters/${character.id}`);
                 if (fullCharacterData && !fullCharacterData.error) {
                    openCharacterModal(fullCharacterData);
                 } else {
                    showError(galleryErrorAlert, `Failed to load details for ${character.name || 'character'}: ${fullCharacterData?.error || 'Unknown error'}`);
                 }
            });

            return card;
        }

        function renderVariationCard(variation) {
            const card = document.createElement('div');
            card.className = 'col-md-4 mb-3';
            const details = [];
            if (variation.pose) details.push(`Pose: ${variation.pose}`);
            if (variation.expression) details.push(`Expression: ${variation.expression}`);
            if (variation.setting) details.push(`Setting: ${variation.setting}`);
             // CHANGED: Use static path correctly
             const imagePath = variation.image_path ? `/static/${variation.image_path}` : '/static/images/placeholder.png';

            card.innerHTML = `
                <div class="card h-100">
                    <img src="${imagePath}" class="variation-image card-img-top" alt="Character Variation" loading="lazy">
                    <div class="card-body p-2">
                        <p class="card-text small text-muted">${details.join('<br>') || 'Base Variation'}</p>
                    </div>
                </div>
            `;
            return card;
        }

        function openCharacterModal(character) {
             currentCharacterId = character.id; // Store current ID
            document.getElementById('characterModalTitle').textContent = character.name || 'Unnamed Character';
            document.getElementById('characterModalName').textContent = character.name || 'Unnamed Character';
            document.getElementById('characterModalDescription').textContent = character.description;
             // CHANGED: Use static path correctly
             document.getElementById('characterModalImage').src = character.base_image_path ? `/static/${character.base_image_path}` : '/static/images/placeholder.png';
            document.getElementById('characterIdForVariation').value = character.id;
             // ADDED: Display ID and dates
             document.getElementById('characterModalId').textContent = `ID: ${character.id}`;
             document.getElementById('characterModalDates').textContent = `Created: ${new Date(character.created_at).toLocaleString()} | Updated: ${new Date(character.updated_at).toLocaleString()}`;


            variationsGallery.innerHTML = ''; // Clear previous variations
            if (character.variations && character.variations.length > 0) {
                noVariationsMessage.style.display = 'none';
                character.variations.forEach(variation => {
                    variationsGallery.appendChild(renderVariationCard(variation));
                });
            } else {
                noVariationsMessage.style.display = 'block';
                variationsGallery.appendChild(noVariationsMessage); // Keep message inside gallery div
            }

            characterDetailModal.show();
        }

        // --- Event Listeners ---
        characterForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const name = document.getElementById('characterName').value.trim();
            const description = document.getElementById('characterDescription').value.trim();
            if (!description) {
                showError(createErrorAlert, 'Character description is required.');
                return;
            }

            const characterData = { description };
            if (name) characterData.name = name;

            const submitButton = characterForm.querySelector('button[type="submit"]');
            submitButton.disabled = true; // Disable button during request

            const newCharacter = await createCharacter(characterData);

            submitButton.disabled = false; // Re-enable button

            if (newCharacter) {
                characterForm.reset();
                await loadCharacters(); // Refresh gallery
            }
        });

        variationForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const characterId = document.getElementById('characterIdForVariation').value;
            const pose = document.getElementById('poseInput').value.trim();
            const expression = document.getElementById('expressionInput').value.trim();
            const setting = document.getElementById('settingInput').value.trim();

            if (!pose && !expression && !setting) {
                 showError(variationErrorAlert, 'Please provide at least one variation parameter (pose, expression, or setting).');
                return;
            }

            const variationData = { pose, expression, setting };
            const submitButton = variationForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;

            const updatedCharacter = await createVariation(characterId, variationData);

             submitButton.disabled = false;

            if (updatedCharacter) {
                variationForm.reset();
                // Re-open/update the modal with the new data
                openCharacterModal(updatedCharacter);
                await loadCharacters(); // Refresh the main gallery as well (optional, but good for consistency)
            }
        });

        // ADDED: Delete button listener
         deleteCharacterBtn.addEventListener('click', async () => {
             if (!currentCharacterId) return;

             if (confirm(`Are you sure you want to delete this character (${document.getElementById('characterModalName').textContent}) and all its images? This cannot be undone.`)) {
                 const success = await deleteCharacter(currentCharacterId);
                 if (success) {
                     characterDetailModal.hide(); // Close modal on success
                     await loadCharacters(); // Refresh gallery
                 }
                 // Error is shown by deleteCharacter function
             }
         });

         // Ensure modal state is reset when closed (especially currentCharacterId)
         characterDetailModalEl.addEventListener('hidden.bs.modal', () => {
             currentCharacterId = null;
             variationForm.reset(); // Reset variation form as well
             hideError(variationErrorAlert); // Hide any lingering errors in modal
         });

        // --- Initialization ---
        async function loadCharacters() {
            // Show initial loading state
             noCharactersMessage.textContent = 'Loading characters...';
             noCharactersMessage.style.display = 'block';
             characterGallery.innerHTML = ''; // Clear gallery before loading
             characterGallery.appendChild(noCharactersMessage); // Add message back

             const characters = await fetchCharacters();

             characterGallery.innerHTML = ''; // Clear loading message/previous content
            if (characters.length > 0) {
                noCharactersMessage.style.display = 'none';
                characters.forEach(character => {
                    characterGallery.appendChild(renderCharacterCard(character));
                });
            } else {
                 // Check if there was an error or genuinely no characters
                 if (!galleryErrorAlert.classList.contains('d-none')) {
                     noCharactersMessage.textContent = 'Could not load characters. See error above.';
                 } else {
                     noCharactersMessage.textContent = 'No characters created yet. Create one above!';
                 }
                noCharactersMessage.style.display = 'block';
                characterGallery.appendChild(noCharactersMessage);
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            // Initial load requires API key, so maybe prompt user or load only after key is entered?
            // For simplicity, let's try loading immediately. If the key isn't ready, fetch will fail gracefully.
            loadCharacters();
            // Add listener to reload if API key changes (optional)
            // apiKeyInput.addEventListener('change', loadCharacters);
        });
    </script>
</body>
</html>
```

**13. `.gitignore` (Recommended)**

Create a `.gitignore` file in the root directory:

```gitignore
# Virtual Environment
venv/
*.venv/
env/
ENV/

# Python cache files
__pycache__/
*.pyc
*.pyo
*.pyd

# Configuration secrets
.env

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Build artifacts
build/
dist/
*.egg-info/

# Static images (if you don't want to commit generated content)
# Consider if you *do* want to commit placeholder images or examples
# static/images/*
# !static/images/placeholder.png

# Database files (if using SQLite later)
*.db
*.sqlite
*.sqlite3

# OS generated files
.DS_Store
Thumbs.db
```

---

This updated plan provides a more robust and secure MVP foundation, addressing the critical issues identified earlier while keeping the scope manageable. Remember to replace placeholders (like API keys in `.env`) and consider the "Known Limitations" for future development iterations.