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
    print("\n" + "=" * 80)
    print("Testing Groq API")
    print("=" * 80)

    if not Config.GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY not found in environment")
        print("   Set it in your .env file or via Settings & Tools in the UI")
        return False

    print(f"[OK] API Key found: {Config.GROQ_API_KEY[:10]}...")

    try:
        from groq import Groq
        client = Groq(api_key=Config.GROQ_API_KEY)
        print("[OK] Groq client initialized")

        # Test with a simple completion (cheaper than transcription)
        print("\nTesting API connection with a simple request...")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            model="llama-3.3-70b-versatile",  # Updated to current model
            max_tokens=10,
        )

        result = response.choices[0].message.content
        print(f"[OK] API Response: {result}")

        print("\n[SUCCESS] Groq API is working correctly!")
        print("   You can use 'groq' for transcription and classification backends")
        return True

    except ImportError:
        print("[ERROR] Groq package not installed")
        print("   Install with: pip install groq")
        return False
    except Exception as e:
        print(f"[ERROR] Error testing Groq API: {e}")
        print("   Check that your API key is valid")
        return False


def test_huggingface_api():
    """Test Hugging Face API connection."""
    print("\n" + "=" * 80)
    print("Testing Hugging Face API")
    print("=" * 80)

    if not Config.HUGGING_FACE_API_KEY:
        print("[ERROR] HUGGING_FACE_API_KEY not found in environment")
        print("   Set it in your .env file or via Settings & Tools in the UI")
        return False

    print(f"[OK] API Key found: {Config.HUGGING_FACE_API_KEY[:10]}...")

    try:
        # Use the huggingface_hub library for authentication test
        from huggingface_hub import HfApi

        print("\nTesting API authentication...")
        api = HfApi(token=Config.HUGGING_FACE_API_KEY)

        # Try to get user info - this validates the token
        user_info = api.whoami()
        username = user_info.get("name", "unknown")

        print(f"[OK] Authenticated as: {username}")
        print("\n[SUCCESS] Hugging Face API is working correctly!")
        print("   You can use 'hf_api' for the diarization backend")
        return True

    except ImportError:
        print("[ERROR] 'huggingface_hub' package not installed")
        print("   Install with: pip install huggingface-hub")
        return False
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Invalid token" in error_msg:
            print("[ERROR] Authentication failed: Invalid API key")
            print("   Check that your HF token is correct")
        elif "403" in error_msg:
            print("[ERROR] Authorization failed: Token lacks required permissions")
            print("   Ensure your token has 'Make calls to Inference Providers' permission")
        else:
            print(f"[ERROR] Error testing Hugging Face API: {error_msg}")
            print("   Check your internet connection and API key")
        return False


def main():
    """Run all API tests."""
    print("=" * 80)
    print("API Key Validation Test Suite")
    print("=" * 80)
    print("\nThis script tests your cloud API configurations.")
    print("Make sure you've set your API keys in .env or via the UI.")

    groq_ok = test_groq_api()
    hf_ok = test_huggingface_api()

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Groq API:        {'[PASS]' if groq_ok else '[FAIL]'}")
    print(f"Hugging Face API: {'[PASS]' if hf_ok else '[FAIL]'}")

    if groq_ok and hf_ok:
        print("\n[SUCCESS] All APIs are configured correctly!")
        print("\nYou can now use cloud backends in the UI:")
        print("  - Transcription: Select 'groq' backend")
        print("  - Diarization: Select 'hf_api' backend")
        print("  - Classification: Select 'groq' backend")
    elif groq_ok or hf_ok:
        print("\n[WARNING] Some APIs are working, but not all")
        print("  Set the missing API keys to enable all cloud features")
    else:
        print("\n[ERROR] No APIs are configured")
        print("  Add your API keys to .env or via Settings & Tools in the UI")

    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
