# Prospect Analyzer

AI-powered prospect research agent that analyzes e-commerce websites for Digital Product Passport (DPP) readiness. Uses Anthropic's Managed Agents API to perform deep analysis and generate branded HTML reports.

## What it does

1. Takes a website URL as input
2. An AI agent crawls the site, analyzes product pages, sustainability claims, supply chain transparency, and compliance signals
3. Produces a detailed Markdown analysis with a DPP readiness score (0-10)
4. Generates a branded HTML report suitable for sharing with prospects
5. Optionally deploys reports to a static hosting service (Netlify)

## Prerequisites

- Python 3.10+
- Anthropic API key with Managed Agents access
- (Optional) Netlify site for report hosting

## Setup

```bash
# Clone the repo
git clone https://github.com/jamnyjakub700-cloud/prospect-analyzer.git
cd prospect-analyzer

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Anthropic API key

# Configure agent (copy and edit with your agent/environment IDs)
cp config.json.example config.json
```

### Create the Managed Agent

```bash
python setup_agent.py
```

This creates an agent and environment via the Anthropic API. The resulting IDs are saved to `config.json`.

## Usage

### Run an analysis

```bash
python run_analysis.py https://www.example-shop.com
```

Output is saved to `output/{domain}-analysis.md`.

### Generate HTML reports

```bash
python generate_site.py
```

Converts all Markdown analyses in `output/` to branded HTML files in `site/`.

### Deploy to Netlify (optional)

```bash
./deploy.sh
```

Copies HTML reports to your Netlify-connected repo and pushes.

## Configuration

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `COMPANY_NAME` | No | Your company name for HTML reports |
| `CONTACT_EMAIL` | No | Contact email in report footer |
| `COMPANY_WEBSITE` | No | Website URL in report footer |
| `CTA_URL` | No | Calendly/booking link for CTA button |
| `NETLIFY_BASE_URL` | No | Base URL of your Netlify site |
| `PROPOSALS_DIR` | No | Path to your Netlify-connected git repo |

### config.json

Contains Managed Agent configuration (agent ID, environment ID, model). Created by `setup_agent.py`.

## Project structure

```
prospect-analyzer/
├── setup_agent.py       # One-time agent creation via Anthropic API
├── run_analysis.py      # Run analysis on a target URL
├── html_generator.py    # Markdown -> branded HTML conversion
├── generate_site.py     # Batch HTML generation + index page
├── deploy.sh            # Deploy HTML reports to Netlify
├── config.json.example  # Agent config template
├── .env.example         # Environment variables template
└── requirements.txt     # Python dependencies
```

## How the agent works

The Managed Agent uses Anthropic's hosted agent infrastructure with:

- **SSE streaming** for real-time output
- **Tool use** for web browsing, content extraction, and analysis
- **Structured output** with DPP readiness scoring across multiple dimensions

The agent evaluates: product data completeness, material/composition info, sustainability claims, supply chain transparency, existing compliance signals, and technical infrastructure readiness.

## Author

**Jakub Jamny** — AI automation specialist

- [LinkedIn](https://www.linkedin.com/in/jakub-jamn%C3%BD-3a0410246)
- [Website](https://jakubjamny.com)
