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

def test_basic_image_generation(model_name):
    logger.info(f"Testing basic image generation with model: {model_name}")
    
    try:
        # Basic image generation without seed
        response = client.images.generate(
            model=model_name,
            prompt="A simple red apple on a white background",
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        logger.info(f"Success! Image generation works with {model_name}.")
        logger.info(f"Generated image URL: {response.data[0].url}")
            
    except Exception as e:
        logger.error(f"Error with {model_name}: {str(e)}")

if __name__ == "__main__":
    # Test both DALL-E 3 and GPT-4o
    test_basic_image_generation("dall-e-3")
    
    try:
        test_basic_image_generation("gpt-4o")
    except Exception as e:
        logger.error(f"GPT-4o test failed: {str(e)}")
 