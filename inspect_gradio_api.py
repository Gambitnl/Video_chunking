"""Inspect the Gradio API to find available endpoints"""
import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from gradio_client import Client

print("Connecting to Gradio server...")
client = Client("http://127.0.0.1:7860")

print("\nAvailable API endpoints:")
print("="*70)

# View the client info
print(f"View info: {client.view_api()}")

print("\nClient attribute names:")
print(dir(client))

print("\n" + "="*70)
print("Use these API names with client.predict(api_name='...')")
