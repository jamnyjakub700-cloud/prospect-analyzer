"""
run_analysis.py — Run prospect analysis via Managed Agents API.

Takes a URL as argument, creates a session, sends instructions, and streams the response.
Output is saved to output/{domain}-analysis.md.
"""

import json
import os
import sys
import re
import threading
import time
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from industry_config import (
    COMPANY_NAME, USER_MESSAGE_TEMPLATE, SESSION_TITLE_TEMPLATE,
    DEPLOY_FILE_SUFFIX,
)

load_dotenv()

# === Configuration ===
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = "https://api.anthropic.com"
# Different endpoints require different beta headers:
# - agents, environments, sessions (CRUD): managed-agents-2026-04-01
# - session events (send): managed-agents-2026-04-01 + ?beta=true
# - session stream (SSE): agent-api-2026-03-01 + ?beta=true
MANAGED_BETA = "managed-agents-2026-04-01"
STREAM_BETA = "agent-api-2026-03-01"
CONFIG_FILE = "config.json"
OUTPUT_DIR = "output"

# Headers for CRUD operations (agents, environments, sessions)
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-beta": MANAGED_BETA,
    "content-type": "application/json",
}


def load_config():
    """Load agent_id and environment_id from config.json"""
    if not os.path.exists(CONFIG_FILE):
        print("ERROR: config.json not found. First run: python setup_agent.py")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def create_session(agent_id, environment_id, url):
    """Create a new session via POST /v1/sessions"""
    domain = urlparse(url).netloc
    print(f">>> Creating session for analysis: {domain}")

    payload = {
        "agent": agent_id,
        "environment_id": environment_id,
        "title": SESSION_TITLE_TEMPLATE.format(domain=domain),
    }

    response = requests.post(
        f"{BASE_URL}/v1/sessions",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Failed to create session: {response.status_code}")

    data = response.json()
    print(f"    Session ID: {data['id']}")
    return data


def send_message(session_id, url):
    """Send a user event with analysis instructions"""
    print(f">>> Sending analysis instructions for {url}...")

    payload = {
        "events": [
            {
                "type": "user.message",
                "content": [
                    {
                        "type": "text",
                        "text": USER_MESSAGE_TEMPLATE.format(url=url),
                    }
                ],
            }
        ]
    }

    # Send events uses managed-agents header + ?beta=true query param
    response = requests.post(
        f"{BASE_URL}/v1/sessions/{session_id}/events?beta=true",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Failed to send message: {response.status_code}")

    return response.json()


def stream_response(session_id):
    """Stream SSE responses from the session and collect text output"""
    print(">>> Streaming agent response...\n")
    print("-" * 60)

    # Stream endpoint requires agent-api beta header + ?beta=true
    stream_headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": STREAM_BETA,
        "Accept": "text/event-stream",
    }

    response = requests.get(
        f"{BASE_URL}/v1/sessions/{session_id}/stream?beta=true",
        headers=stream_headers,
        stream=True,
    )

    if response.status_code != 200:
        print(f"Stream error: {response.status_code} — {response.text}")
        raise Exception(f"Stream failed: {response.status_code}")

    # Force UTF-8 encoding — API returns UTF-8 but requests may not detect it
    response.encoding = "utf-8"

    # Collect full text output for saving to file
    full_text = []

    # Parse SSE events (format: "event: message\ndata: {json}\n\n")
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue

        json_str = line[6:]  # Remove "data: " prefix

        try:
            event = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        if event_type == "agent":
            for block in event.get("content", []):
                if block.get("type") == "text":
                    text = block["text"]
                    print(text, end="", flush=True)
                    full_text.append(text)

        elif event_type == "tool_use":
            tool_name = event.get("name", "unknown")
            print(f"\n[Tool: {tool_name}]", flush=True)

        elif event_type == "tool_result":
            pass

        elif event_type == "status_idle":
            print("\n" + "-" * 60)
            print(">>> Agent completed analysis.")
            usage = event.get("usage", {})
            if usage:
                print(f"    Input tokens: {usage.get('input_tokens', 'N/A')}")
                print(f"    Output tokens: {usage.get('output_tokens', 'N/A')}")
                print(f"    Duration: {usage.get('duration_seconds', 'N/A')}s")
            break

        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", "Unknown error")
            print(f"\nERROR: {error_msg}")
            break

    return "".join(full_text)


def clean_analysis(text):
    """Remove thinking text from the beginning and internal agent notes"""
    # Find first markdown heading — everything before it is thinking/status text
    match = re.search(r"^(#{1,2}\s)", text, re.MULTILINE)
    if match:
        text = text[match.start():]

    # Remove mentions of internal container paths (/mnt/session/...)
    text = re.sub(r"\n.*?/mnt/session/.*?\n", "\n", text)

    return text.strip()


def save_analysis(url, text):
    """Save final analysis to output/{domain}-analysis.md"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    text = clean_analysis(text)

    domain = urlparse(url).netloc
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
    filename = f"{safe_domain}-analysis.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    print(f">>> Analysis saved: {filepath}")
    return filepath


NETLIFY_BASE_URL = os.environ.get("NETLIFY_BASE_URL", "https://your-site.netlify.app")
PROPOSALS_DIR = os.environ.get("PROPOSALS_DIR", os.path.expanduser("~/proposals"))
PROPOSALS_OUTPUT = os.path.join(PROPOSALS_DIR, "output")


def get_slug_from_md(md_filepath):
    """Extract slug from MD filename (www.example.com-analysis.md -> example-com)."""
    basename = os.path.basename(md_filepath)
    domain_match = re.match(r"(?:www\.)?(.+?)-analysis\.md$", basename)
    if domain_match:
        return domain_match.group(1).replace(".", "-").replace("_", "-")
    return basename.replace(".md", "").replace(".", "-")


def generate_html_version(md_filepath):
    """Generate HTML version of analysis to site/."""
    from html_generator import generate_html as _gen_html

    site_dir = "site"
    os.makedirs(site_dir, exist_ok=True)

    slug = get_slug_from_md(md_filepath)
    html_path = os.path.join(site_dir, f"{slug}.html")

    with open(md_filepath, "r", encoding="utf-8") as f:
        md_text = f.read()

    _gen_html(md_text, html_path)
    print(f">>> HTML version: {html_path}")

    deploy_filename = f"{slug}{DEPLOY_FILE_SUFFIX}"
    print(f">>> Analysis available at: {NETLIFY_BASE_URL}/{deploy_filename}.html")

    return html_path


def deploy_to_netlify(html_path):
    """Copy HTML to proposals repo, commit, and push."""
    import subprocess
    import shutil

    if not os.path.isdir(os.path.join(PROPOSALS_DIR, ".git")):
        print(f"ERROR: {PROPOSALS_DIR} is not a git repo.")
        return False

    basename = os.path.basename(html_path)
    slug = basename.replace(".html", "")
    deploy_name = f"{slug}{DEPLOY_FILE_SUFFIX}.html"
    deploy_path = os.path.join(PROPOSALS_OUTPUT, deploy_name)

    shutil.copy2(html_path, deploy_path)
    print(f">>> Copied: {deploy_path}")

    try:
        subprocess.run(["git", "add", f"output/{deploy_name}"], cwd=PROPOSALS_DIR, check=True)

        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROPOSALS_DIR)
        if result.returncode == 0:
            print(">>> No new changes to commit (file unchanged).")
            return True

        subprocess.run(
            ["git", "commit", "-m", f"Add analysis: {slug} ({time.strftime('%Y-%m-%d')})"],
            cwd=PROPOSALS_DIR, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=PROPOSALS_DIR, check=True)

        print(f">>> Deploy will happen automatically in ~60 seconds.")
        print(f">>> URL: {NETLIFY_BASE_URL}/{deploy_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"ERROR during git operation: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"{COMPANY_NAME} — Website analysis")
    parser.add_argument("url", help="URL of website to analyze")
    parser.add_argument("--html", action="store_true", help="Generate HTML version to site/")
    parser.add_argument("--deploy", action="store_true", help="Generate HTML + deploy to Netlify")
    args = parser.parse_args()

    if args.deploy:
        args.html = True

    url = args.url

    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Check your .env file.")
        sys.exit(1)

    config = load_config()
    agent_id = config["agent_id"]
    environment_id = config["environment_id"]

    print("=" * 60)
    print(f"{COMPANY_NAME} — Analysis")
    print(f"URL: {url}")
    print("=" * 60)

    # Step 1: Create session
    session_data = create_session(agent_id, environment_id, url)
    session_id = session_data["id"]

    # Step 2: Open stream FIRST, then send message (see docs: "open stream first")
    def send_message_threaded():
        time.sleep(1)
        send_message(session_id, url)

    sender = threading.Thread(target=send_message_threaded, daemon=True)
    sender.start()

    # Step 3: Stream responses
    full_text = stream_response(session_id)
    sender.join()

    # Step 4: Save output
    if full_text.strip():
        md_path = save_analysis(url, full_text)

        # Step 5: HTML generation
        if args.html:
            html_path = generate_html_version(md_path)

            # Step 6: Deploy to Netlify
            if args.deploy:
                deploy_to_netlify(html_path)
    else:
        print(">>> Warning: Agent returned no text.")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
