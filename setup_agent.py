"""
setup_agent.py — Create a Managed Agent and Environment via Anthropic API.

Uses raw HTTP requests (requests library) against the Anthropic Managed Agents API.
Beta header: managed-agents-2026-04-01
"""

import json
import os
import requests
from dotenv import load_dotenv
from industry_config import AGENT_NAME, COMPANY_NAME, SYSTEM_PROMPT

load_dotenv()

# === Configuration ===
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = "https://api.anthropic.com"
BETA_HEADER = "managed-agents-2026-04-01"
CONFIG_FILE = "config.json"

# Common headers for all requests
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-beta": BETA_HEADER,
    "content-type": "application/json",
}


def create_agent():
    """Create a Managed Agent via POST /v1/agents"""
    print(">>> Creating agent...")

    payload = {
        "name": AGENT_NAME,
        "model": "claude-sonnet-4-6",
        "system": SYSTEM_PROMPT,
        "tools": [
            {"type": "agent_toolset_20260401"}
        ],
    }

    response = requests.post(
        f"{BASE_URL}/v1/agents",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Failed to create agent: {response.status_code}")

    data = response.json()
    print(f"    Agent ID: {data['id']}")
    print(f"    Version: {data['version']}")
    return data


def create_environment():
    """Create a cloud environment via POST /v1/environments"""
    print(">>> Creating environment...")

    payload = {
        "name": f"{AGENT_NAME}-env",
        "config": {
            "type": "cloud",
            # Unrestricted network access — agent needs to browse websites
            "networking": {"type": "unrestricted"},
        },
    }

    response = requests.post(
        f"{BASE_URL}/v1/environments",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Failed to create environment: {response.status_code}")

    data = response.json()
    print(f"    Environment ID: {data['id']}")
    return data


def save_config(agent_data, environment_data):
    """Save agent_id and environment_id to config.json"""
    config = {
        "agent_id": agent_data["id"],
        "agent_version": agent_data["version"],
        "environment_id": environment_data["id"],
        "model": "claude-sonnet-4-6",
        "beta_header": BETA_HEADER,
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f">>> Configuration saved to {CONFIG_FILE}")
    return config


def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Check your .env file.")
        return

    print("=" * 60)
    print(f"{COMPANY_NAME} — Setup")
    print("=" * 60)

    # Step 1: Create agent
    agent_data = create_agent()

    # Step 2: Create environment
    environment_data = create_environment()

    # Step 3: Save configuration
    config = save_config(agent_data, environment_data)

    print()
    print("=" * 60)
    print("Setup complete! Now you can run an analysis:")
    print(f"  python run_analysis.py https://www.example.com")
    print("=" * 60)


if __name__ == "__main__":
    main()
