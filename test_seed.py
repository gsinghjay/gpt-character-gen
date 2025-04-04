from openai import OpenAI
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Print the OpenAI client version
import openai
logger.info(f"OpenAI Python package version: {openai.__version__}")

def test_image_generation_with_seed():
    try:
        # Try to generate an image with a seed
        seed_value = 123456
        logger.info(f"Attempting to generate image with seed: {seed_value}")
        
        response = client.images.generate(
            model="dall-e-3",
            prompt="A simple red apple on a white background",
            size="1024x1024",
            quality="standard",
            n=1,
            seed=seed_value
        )
        
        logger.info("Success! Seed parameter is supported.")
        logger.info(f"Generated image URL: {response.data[0].url}")
        
        # Try to access the seed in the response
        if hasattr(response.data[0], 'seed'):
            logger.info(f"Response includes seed: {response.data[0].seed}")
        else:
            logger.info("Response does not include a seed value.")
            
    except TypeError as e:
        logger.error(f"TypeError: {str(e)}")
        if "unexpected keyword argument 'seed'" in str(e):
            logger.error("Seed parameter is NOT supported in this version.")
        else:
            logger.error("An unexpected error occurred.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    test_image_generation_with_seed() 