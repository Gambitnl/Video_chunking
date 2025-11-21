"""Test script to validate Groq and Hugging Face API keys."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)


def test_groq_api():
    """Test Groq API connection and basic transcription."""
    logger.info("\n%s", "=" * 80)
    logger.info("Testing Groq API")
    logger.info("%s", "=" * 80)

    if not Config.GROQ_API_KEY:
        logger.error("GROQ_API_KEY not found in environment")
        logger.info("   Set it in your .env file or via Settings & Tools in the UI")
        return False

    logger.info("API Key found: %s...", Config.GROQ_API_KEY[:10])

    try:
        from groq import Groq
        client = Groq(api_key=Config.GROQ_API_KEY)
        logger.info("Groq client initialized")

        # Test with a simple completion (cheaper than transcription)
        logger.info("\nTesting API connection with a simple request...")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            model="llama-3.3-70b-versatile",  # Updated to current model
            max_tokens=10,
        )

        result = response.choices[0].message.content
        logger.info("API Response: %s", result)

        logger.info("\n[SUCCESS] Groq API is working correctly!")
        logger.info("   You can use 'groq' for transcription and classification backends")
        return True

    except ImportError:
        logger.error("Groq package not installed")
        logger.info("   Install with: pip install groq")
        return False
    except Exception as e:
        logger.exception("Error testing Groq API: %s", e)
        logger.info("   Check that your API key is valid")
        return False


def test_huggingface_api():
    """Test Hugging Face API connection."""
    logger.info("\n%s", "=" * 80)
    logger.info("Testing Hugging Face API")
    logger.info("%s", "=" * 80)

    if not Config.HUGGING_FACE_API_KEY:
        logger.error("HUGGING_FACE_API_KEY not found in environment")
        logger.info("   Set it in your .env file or via Settings & Tools in the UI")
        return False

    logger.info("API Key found: %s...", Config.HUGGING_FACE_API_KEY[:10])

    try:
        # Use the huggingface_hub library for authentication test
        from huggingface_hub import HfApi

        logger.info("\nTesting API authentication...")
        api = HfApi(token=Config.HUGGING_FACE_API_KEY)

        # Try to get user info - this validates the token
        user_info = api.whoami()
        username = user_info.get("name", "unknown")

        logger.info("Authenticated as: %s", username)
        logger.info("\n[SUCCESS] Hugging Face API is working correctly!")
        logger.info("   You can use 'hf_api' for the diarization backend")
        return True

    except ImportError:
        logger.error("'huggingface_hub' package not installed")
        logger.info("   Install with: pip install huggingface-hub")
        return False
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Invalid token" in error_msg:
            logger.error("Authentication failed: Invalid API key")
            logger.info("   Check that your HF token is correct")
        elif "403" in error_msg:
            logger.error("Authorization failed: Token lacks required permissions")
            logger.info("   Ensure your token has 'Make calls to Inference Providers' permission")
        else:
            logger.exception("Error testing Hugging Face API: %s", error_msg)
            logger.info("   Check your internet connection and API key")
        return False


def main():
    """Run all API tests."""
    logger.info("%s", "=" * 80)
    logger.info("API Key Validation Test Suite")
    logger.info("%s", "=" * 80)
    logger.info("\nThis script tests your cloud API configurations.")
    logger.info("Make sure you've set your API keys in .env or via the UI.")

    groq_ok = test_groq_api()
    hf_ok = test_huggingface_api()

    logger.info("\n%s", "=" * 80)
    logger.info("Test Summary")
    logger.info("%s", "=" * 80)
    logger.info("Groq API:        %s", "[PASS]" if groq_ok else "[FAIL]")
    logger.info("Hugging Face API: %s", "[PASS]" if hf_ok else "[FAIL]")

    if groq_ok and hf_ok:
        logger.info("\n[SUCCESS] All APIs are configured correctly!")
        logger.info("\nYou can now use cloud backends in the UI:")
        logger.info("  - Transcription: Select 'groq' backend")
        logger.info("  - Diarization: Select 'hf_api' backend")
        logger.info("  - Classification: Select 'groq' backend")
    elif groq_ok or hf_ok:
        logger.warning("\n[WARNING] Some APIs are working, but not all")
        logger.info("  Set the missing API keys to enable all cloud features")
    else:
        logger.error("\n[ERROR] No APIs are configured")
        logger.info("  Add your API keys to .env or via Settings & Tools in the UI")

    logger.info("%s", "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n\nTest interrupted by user")
    except Exception as e:
        logger.exception("\n\nUnexpected error: %s", e)
