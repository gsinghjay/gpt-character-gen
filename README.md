# Fictional Character Creator MVP

An application that generates consistent character portraits from written descriptions using OpenAI's DALL-E 3, allowing for variations in poses, expressions, and settings.

## Features

- Create fictional characters with detailed descriptions and optional names.
- Generate a base character portrait using OpenAI's image generation API.
- Create variations of the base character with different poses, expressions, and settings, aiming for consistency.
- Simple web interface for interacting with the application.
- Basic API key security (`X-API-Key` header).
- Simple file-based JSON storage for character data (MVP limitation).
- Generated images stored locally in the `static/images` directory.

## Technology Stack

- Backend: FastAPI (Python)
- Image Generation: OpenAI API (DALL-E 3)
- HTTP Client: HTTPX
- Storage: Simple file-based JSON storage (`characters_db.json`)
- Frontend: HTML, JavaScript, Bootstrap 5
- Configuration: Pydantic Settings, `.env` file

## Project Structure

```
fictional_character_creator/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       └── characters.py   # Character-related endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration (API keys, etc.)
│   │   └── security.py      # Basic API security
│   ├── db/
│   │   ├── __init__.py
│   │   └── file_storage.py  # Simple file-based storage
│   ├── models/
│   │   ├── __init__.py
│   │   └── character.py     # Character data models
│   └── services/
│       ├── __init__.py
│       └── image_generator.py  # OpenAI integration
├── static/
│   ├── css/
│   ├── js/
│   └── images/              # Store generated images
├── templates/
│   └── index.html           # Web UI
├── requirements.txt
├── README.md
└── .env                     # Store secrets (add to .gitignore)
```

## Setup Instructions

1.  **Clone Repository:**
    ```bash
    git clone <your-repo-url>
    cd fictional_character_creator
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

4.  **Configure Environment Variables:**
    Update the `.env` file with your OpenAI API key and a secure API key for the application:
    ```
    OPENAI_API_KEY="your_openai_api_key_here"
    API_KEY="your_chosen_secret_api_key_for_this_app"
    ```

5.  **Run the Application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The application will be available at http://127.0.0.1:8000

## API Usage

All API endpoints are protected by the API key specified in your `.env` file. When making requests to the API (either via the web UI or directly), you must include the `X-API-Key` header with your API key.

## Known Limitations & Future Improvements

- **Storage:** The current implementation uses a simple JSON file for storage, which is not suitable for production due to race conditions and performance limitations.
- **Error Handling:** Basic error handling is implemented but could be enhanced for production use.
- **Image Generation Consistency:** While the prompt attempts to maintain consistency, AI image generation might still produce variations.
- **Testing:** No automated tests are included in this MVP.
- **Performance:** File I/O operations are synchronous and could be improved for better performance under load.

## License

[Specify your license here] 