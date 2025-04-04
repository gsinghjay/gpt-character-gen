from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from ..core.config import get_settings

settings = get_settings()

API_KEY_NAME = "X-API-Key"  # Standard header name
api_key_header_auth = APIKeyHeader(name=API_KEY_NAME, auto_error=False)  # Set auto_error=False to handle error manually

async def get_api_key(api_key_header: str = Security(api_key_header_auth)):
    """Retrieve and validate API key from the X-API-Key header."""
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
    return api_key_header 