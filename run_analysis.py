"""
run_analysis.py — Spuštěn�� DPP analýzy fashion e-shopu přes Managed Agents API.

Přijme URL jako argument, vytvoří session, pošle instrukci a streamuje odpověď.
Výstup ulož�� do output/{domain}-analysis.md.
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

load_dotenv()

# === Konfigurace ===
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = "https://api.anthropic.com"
# Různé endpointy vyžadují různé beta headery:
# - agents, environments, sessions (CRUD): managed-agents-2026-04-01
# - session events (send): managed-agents-2026-04-01 + ?beta=true
# - session stream (SSE): agent-api-2026-03-01 + ?beta=true
MANAGED_BETA = "managed-agents-2026-04-01"
STREAM_BETA = "agent-api-2026-03-01"
CONFIG_FILE = "config.json"
OUTPUT_DIR = "output"

# Hlavičky pro CRUD operace (agents, environments, sessions)
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-beta": MANAGED_BETA,
    "content-type": "application/json",
}


def nacti_config():
    """Načte agent_id a environment_id z config.json"""
    if not os.path.exists(CONFIG_FILE):
        print("CHYBA: config.json neexistuje. Nejdřív spusť: python setup_agent.py")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def vytvor_session(agent_id, environment_id, url):
    """Vytvoří novou session přes POST /v1/sessions"""
    domain = urlparse(url).netloc
    print(f">>> Vytvářím session pro analýzu: {domain}")

    payload = {
        "agent": agent_id,
        "environment_id": environment_id,
        "title": f"DPP analýza: {domain}",
    }

    response = requests.post(
        f"{BASE_URL}/v1/sessions",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Nepodařilo se vytvo��it session: {response.status_code}")

    data = response.json()
    print(f"    Session ID: {data['id']}")
    return data


def posli_zpravu(session_id, url):
    """Pošle user event s instrukcí analyzovat daný web"""
    print(f">>> Posílám instrukci k analýze {url}...")

    payload = {
        "events": [
            {
                "type": "user.message",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Analyzuj tento fashion e-shop: {url}\n\n"
                            "Projdi web, podívej se na produktové stránky, zjisti jaké materiály "
                            "používají, jaké mají ceny, kolik mají produktů.\n\n"
                            "Potom vytvoř kompletní DPP readiness analýzu podle ESPR požadavků "
                            "pro textil. Výstup napiš v češtině."
                        ),
                    }
                ],
            }
        ]
    }

    # Send events používá managed-agents header + ?beta=true query param
    response = requests.post(
        f"{BASE_URL}/v1/sessions/{session_id}/events?beta=true",
        headers=HEADERS,
        json=payload,
    )

    print(f"    Status: {response.status_code}")

    if response.status_code != 200:
        print(f"    Error: {response.text}")
        raise Exception(f"Nepodařilo se poslat zprávu: {response.status_code}")

    return response.json()


def streamuj_odpoved(session_id):
    """Streamuje SSE odpovědi ze session a sbírá textový výstup"""
    print(">>> Streamuji odpověď agenta...\n")
    print("-" * 60)

    # Stream endpoint vyžaduje agent-api beta header + ?beta=true
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
        print(f"CHYBA streamu: {response.status_code} — {response.text}")
        raise Exception(f"Stream selhal: {response.status_code}")

    # Forcujeme UTF-8 encoding — API vrací UTF-8, ale requests to nemusí detekovat
    response.encoding = "utf-8"

    # Sbíráme celý textový výstup pro uložení do souboru
    full_text = []

    # Parsování SSE eventů (formát: "event: message\ndata: {json}\n\n")
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue

        json_str = line[6:]  # Odstraň prefix "data: "

        try:
            event = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        # Reálný formát eventů ze streamu:
        # type="agent" + content[].type="text" — textová odpověď
        # type="agent" + content[].type="thinking" — thinking blok
        # type="tool_use" / type="tool_result" — nástroje
        # type="status_idle" — agent dokončil
        # type="model_request_start" / "model_request_end" — span eventy

        if event_type == "agent":
            # Agentova zpráva — může obsahovat text i thinking bloky
            for block in event.get("content", []):
                if block.get("type") == "text":
                    text = block["text"]
                    print(text, end="", flush=True)
                    full_text.append(text)

        elif event_type == "tool_use":
            # Agent používá nástroj
            tool_name = event.get("name", "unknown")
            print(f"\n[Nástroj: {tool_name}]", flush=True)

        elif event_type == "tool_result":
            # Výsledek nástroje — nemusíme vypisovat
            pass

        elif event_type == "status_idle":
            # Agent dokončil práci
            print("\n" + "-" * 60)
            print(">>> Agent dokončil analýzu.")
            # Vypíšeme usage stats pokud jsou k dispozici
            usage = event.get("usage", {})
            if usage:
                print(f"    Input tokens: {usage.get('input_tokens', 'N/A')}")
                print(f"    Output tokens: {usage.get('output_tokens', 'N/A')}")
                print(f"    Doba běhu: {usage.get('duration_seconds', 'N/A')}s")
            break

        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", "Neznámá chyba")
            print(f"\nCHYBA: {error_msg}")
            break

    return "".join(full_text)


def vycisti_analyzu(text):
    """Odstraní thinking text ze začátku a interní poznámky agenta"""
    # Najdi první markdown heading — vše před ním je thinking/status text
    match = re.search(r"^(#{1,2}\s)", text, re.MULTILINE)
    if match:
        text = text[match.start():]

    # Odstraň zmínky o interních cestách kontejneru (/mnt/session/...)
    text = re.sub(r"\n.*?/mnt/session/.*?\n", "\n", text)

    return text.strip()


def uloz_analyzu(url, text):
    """Uloží finální analýzu do output/{domain}-analysis.md"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Vyčisti thinking text a interní poznámky
    text = vycisti_analyzu(text)

    domain = urlparse(url).netloc
    # Vyčisti doménové jméno pro název souboru
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
    filename = f"{safe_domain}-analysis.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    print(f">>> Analýza uložena: {filepath}")
    return filepath


NETLIFY_BASE_URL = os.environ.get("NETLIFY_BASE_URL", "https://your-site.netlify.app")
PROPOSALS_DIR = os.environ.get("PROPOSALS_DIR", os.path.expanduser("~/proposals"))
PROPOSALS_OUTPUT = os.path.join(PROPOSALS_DIR, "output")


def _slug_z_md(md_filepath):
    """Extrahuje slug z názvu MD souboru (www.laklara.cz-analysis.md → laklara-cz)."""
    basename = os.path.basename(md_filepath)
    domain_match = re.match(r"(?:www\.)?(.+?)-analysis\.md$", basename)
    if domain_match:
        return domain_match.group(1).replace(".", "-").replace("_", "-")
    return basename.replace(".md", "").replace(".", "-")


def generuj_html_verzi(md_filepath):
    """Vygeneruje HTML verzi analýzy do site/."""
    from html_generator import generuj_html as _gen_html

    site_dir = "site"
    os.makedirs(site_dir, exist_ok=True)

    slug = _slug_z_md(md_filepath)
    html_path = os.path.join(site_dir, f"{slug}.html")

    with open(md_filepath, "r", encoding="utf-8") as f:
        md_text = f.read()

    _gen_html(md_text, html_path)
    print(f">>> HTML verze: {html_path}")

    # Výpis URL kde bude analýza dostupná po deployi
    deploy_filename = f"{slug}-dpp-analysis"
    print(f">>> Analýza dostupná na: {NETLIFY_BASE_URL}/{deploy_filename}.html")

    return html_path


def deploy_na_netlify(html_path):
    """Zkopíruje HTML do cyrcid-proposals/output/, commitne a pushne."""
    import subprocess

    if not os.path.isdir(os.path.join(PROPOSALS_DIR, ".git")):
        print(f"CHYBA: {PROPOSALS_DIR} není git repo.")
        return False

    # Název souboru pro deploy: laklara-cz.html → laklara-cz-dpp-analysis.html
    basename = os.path.basename(html_path)
    slug = basename.replace(".html", "")
    deploy_name = f"{slug}-dpp-analysis.html"
    deploy_path = os.path.join(PROPOSALS_OUTPUT, deploy_name)

    # Zkopíruj
    import shutil
    shutil.copy2(html_path, deploy_path)
    print(f">>> Zkopírováno: {deploy_path}")

    # Git add + commit + push
    try:
        subprocess.run(["git", "add", f"output/{deploy_name}"], cwd=PROPOSALS_DIR, check=True)

        # Zkontroluj jestli jsou změny
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROPOSALS_DIR)
        if result.returncode == 0:
            print(">>> Žádné nové změny k commitnutí (soubor se nezměnil).")
            return True

        subprocess.run(
            ["git", "commit", "-m", f"Add DPP analysis: {slug} ({time.strftime('%Y-%m-%d')})"],
            cwd=PROPOSALS_DIR, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=PROPOSALS_DIR, check=True)

        print(f">>> Deploy proběhne automaticky za ~60 sekund.")
        print(f">>> URL: {NETLIFY_BASE_URL}/{deploy_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"CHYBA při git operaci: {e}")
        return False


def main():
    # Parsování argumentů
    import argparse
    parser = argparse.ArgumentParser(description="cyrcID Prospect Analyzer — DPP analýza fashion e-shopů")
    parser.add_argument("url", help="URL fashion e-shopu k analýze")
    parser.add_argument("--html", action="store_true", help="Vygeneruje i HTML verzi do site/")
    parser.add_argument("--deploy", action="store_true", help="Vygeneruje HTML + deployne na Netlify (přes cyrcid-proposals)")
    args = parser.parse_args()

    # --deploy implikuje --html
    if args.deploy:
        args.html = True

    url = args.url

    if not API_KEY:
        print("CHYBA: ANTHROPIC_API_KEY není nastavený. Zkontroluj .env soubor.")
        sys.exit(1)

    # Načti konfiguraci (agent_id, environment_id)
    config = nacti_config()
    agent_id = config["agent_id"]
    environment_id = config["environment_id"]

    print("=" * 60)
    print(f"cyrcID Prospect Analyzer — DPP Analýza")
    print(f"URL: {url}")
    print("=" * 60)

    # Krok 1: Vytvoř session
    session_data = vytvor_session(agent_id, environment_id, url)
    session_id = session_data["id"]

    # Krok 2: Otevři stream PRVNÍ, pak pošli zprávu (viz docs: "open stream first")
    def posli_zpravu_threaded():
        time.sleep(1)
        posli_zpravu(session_id, url)

    sender = threading.Thread(target=posli_zpravu_threaded, daemon=True)
    sender.start()

    # Krok 3: Streamuj odpovědi
    full_text = streamuj_odpoved(session_id)
    sender.join()

    # Krok 4: Ulož výstup
    if full_text.strip():
        md_path = uloz_analyzu(url, full_text)

        # Krok 5: HTML generování
        if args.html:
            html_path = generuj_html_verzi(md_path)

            # Krok 6: Deploy na Netlify
            if args.deploy:
                deploy_na_netlify(html_path)
    else:
        print(">>> Varování: Agent nevrátil žádný text.")

    print()
    print("Hotovo!")


if __name__ == "__main__":
    main()
