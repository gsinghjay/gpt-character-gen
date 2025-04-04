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

def test_image_generation_with_model(model_name):
    logger.info(f"Testing image generation with model: {model_name}")
    
    try:
        # Try to generate an image with a seed
        seed_value = 123456
        logger.info(f"Attempting to generate image with seed: {seed_value}")
        
        response = client.images.generate(
            model=model_name,
            prompt="A simple red apple on a white background",
            size="1024x1024",
            quality="standard",
            n=1,
            seed=seed_value
        )
        
        logger.info(f"Success! Seed parameter is supported for {model_name}.")
        logger.info(f"Generated image URL: {response.data[0].url}")
        
        # Try to access the seed in the response
        if hasattr(response.data[0], 'seed'):
            logger.info(f"Response includes seed: {response.data[0].seed}")
        else:
            logger.info("Response does not include a seed value.")
            
    except TypeError as e:
        logger.error(f"TypeError: {str(e)}")
        if "unexpected keyword argument 'seed'" in str(e):
            logger.error(f"Seed parameter is NOT supported for {model_name} in this version.")
        else:
            logger.error(f"An unexpected error occurred with {model_name}.")
    except Exception as e:
        logger.error(f"Error with {model_name}: {str(e)}")

if __name__ == "__main__":
    # Test DALL-E 3 first
    test_image_generation_with_model("dall-e-3")
    
    # Then test GPT-4o if it supports image generation
    try:
        test_image_generation_with_model("gpt-4o")
    except Exception as e:
        logger.error(f"GPT-4o test failed: {str(e)}")
        logger.error("GPT-4o may not support direct image generation through the images.generate API") 