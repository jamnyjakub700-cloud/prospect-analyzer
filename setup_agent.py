"""
setup_agent.py — Vytvoření Managed Agent a Environment pro DPP analýzu fashion brandů.

Používá raw HTTP requesty (requests knihovna) proti Anthropic Managed Agents API.
Beta header: managed-agents-2026-04-01
"""

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# === Konfigurace ===
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = "https://api.anthropic.com"
BETA_HEADER = "managed-agents-2026-04-01"
CONFIG_FILE = "config.json"

# Společné hlavičky pro všechny requesty
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-beta": BETA_HEADER,
    "content-type": "application/json",
}

# System prompt zaměřený na DPP analýzu fashion e-shopů
SYSTEM_PROMPT = """Jsi expert na Digital Product Passports (DPP) podle nařízení ESPR (Ecodesign for Sustainable Products Regulation) pro textilní průmysl.

Tvůj úkol:
1. Navštiv zadaný e-shop (URL) a prozkoumej jeho produkty.
2. Identifikuj: název značky, typy produktů, použité materiály, cenové rozpětí, počet produktů.
3. Zanalyzuj DPP readiness — jaká data značka již má a jaká bude potřebovat podle ESPR pro textil.

ESPR požadavky pro textil (platné od 2028):
- Složení materiálů (přesné % podíly vláken)
- Země původu / výroby
- Informace o opravitelnosti a recyklovatelnosti
- Uhlíková stopa (Carbon Footprint) a LCA data
- Informace o dodavatelském řetězci (supply chain traceability)
- Návod na údržbu a prodloužení životnosti
- Informace o nebezpečných látkách (REACH compliance)
- QR kód / digitální nosič pro přístup k DPP

Výstup napiš v češtině jako strukturovanou analýzu (~1 strana A4):

# DPP Analýza: [Název značky]

## 1. Profil značky
(název, web, segment, cenové rozpětí, počet produktů)

## 2. Produktové portfolio
(typy produktů, hlavní materiály, kategorie)

## 3. Současný stav dat
(jaké informace značka už uvádí na webu — materiály, složení, země původu atd.)

## 4. DPP Gap analýza
(co chybí pro splnění ESPR požadavků — tabulka s checklistem)

## 5. Doporučení
(konkrétní kroky pro přípravu na DPP, prioritizované podle náročnosti)

## 6. Shrnutí
(celkové DPP readiness skóre 1-10, hlavní rizika, odhadovaná náročnost implementace)

Používej data přímo z webu. Buď konkrétní — uváděj příklady produktů a cen."""


def vytvor_agenta():
    """Vytvoří Managed Agent přes POST /v1/agents"""
    print(">>> Vytvářím agenta...")

    payload = {
        "name": "cyrcid-prospect-analyzer",
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
        raise Exception(f"Nepodařilo se vytvořit agenta: {response.status_code}")

    data = response.json()
    print(f"    Agent ID: {data['id']}")
    print(f"    Version: {data['version']}")
    return data


def vytvor_environment():
    """Vytvoří cloud environment přes POST /v1/environments"""
    print(">>> Vytvářím environment...")

    payload = {
        "name": "prospect-analyzer-env",
        "config": {
            "type": "cloud",
            # Neomezený síťový přístup — agent potřebuje přistupovat k webům
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
        raise Exception(f"Nepodařilo se vytvořit environment: {response.status_code}")

    data = response.json()
    print(f"    Environment ID: {data['id']}")
    return data


def uloz_config(agent_data, environment_data):
    """Uloží agent_id a environment_id do config.json"""
    config = {
        "agent_id": agent_data["id"],
        "agent_version": agent_data["version"],
        "environment_id": environment_data["id"],
        "model": "claude-sonnet-4-6",
        "beta_header": BETA_HEADER,
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f">>> Konfigurace uložena do {CONFIG_FILE}")
    return config


def main():
    if not API_KEY:
        print("CHYBA: ANTHROPIC_API_KEY není nastavený. Zkontroluj .env soubor.")
        return

    print("=" * 60)
    print("cyrcID Prospect Analyzer — Setup")
    print("=" * 60)

    # Krok 1: Vytvoř agenta
    agent_data = vytvor_agenta()

    # Krok 2: Vytvoř environment
    environment_data = vytvor_environment()

    # Krok 3: Ulož konfiguraci
    config = uloz_config(agent_data, environment_data)

    print()
    print("=" * 60)
    print("Setup dokončen! Nyní můžeš spustit analýzu:")
    print(f"  python run_analysis.py https://www.laklara.cz")
    print("=" * 60)


if __name__ == "__main__":
    main()
