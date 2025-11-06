"""Inspect the Gradio API to find available endpoints"""
import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from gradio_client import Client
from src.logger import get_logger


logger = get_logger(__name__)

logger.info("Connecting to Gradio server...")
client = Client("http://127.0.0.1:7860")

logger.info("Available API endpoints:")
logger.info("=" * 70)

# View the client info
logger.info("View info: %s", client.view_api())

logger.info("Client attribute names: %s", dir(client))

logger.info("=" * 70)
logger.info("Use these API names with client.predict(api_name='...')")
