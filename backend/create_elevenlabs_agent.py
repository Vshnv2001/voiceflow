import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    print("Error: ELEVENLABS_API_KEY not found in environment variables")
    exit(1)

# Prepare the curl command
curl_command = [
    "curl",
    "-X", "POST",
    "https://api.elevenlabs.io/v1/convai/agents/create",
    "-H", f"xi-api-key: {api_key}",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({
        "conversation_config": {}
    })
]

try:
    # Execute the curl command
    result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
    
    # Parse the response
    response_data = json.loads(result.stdout)
    print(f"Agent created successfully: {json.dumps(response_data, indent=2)}")
    
except subprocess.CalledProcessError as e:
    print(f"Error executing curl command: {e}")
    print(f"Error output: {e.stderr}")
except json.JSONDecodeError as e:
    print(f"Error parsing JSON response: {e}")
    print(f"Raw response: {result.stdout}")
except Exception as e:
    print(f"Unexpected error: {e}")