# Prospect Analyzer

AI-powered prospect research agent that analyzes websites and generates branded HTML reports. Uses Anthropic's Managed Agents API to perform deep analysis with configurable industry-specific criteria.

## What it does

1. Takes a website URL as input
2. An AI agent crawls the site, analyzes content, products, and compliance signals
3. Produces a detailed Markdown analysis with a readiness score (0-10)
4. Generates a branded HTML report suitable for sharing with prospects
5. Optionally deploys reports to a static hosting service (Netlify)

**Fully configurable** — change `industry_config.py` to analyze any industry (compliance, security, UX, sustainability, etc.).

## Prerequisites

- Python 3.10+
- Anthropic API key with Managed Agents access
- (Optional) Netlify site for report hosting

## Quick Start

1. **Clone and install dependencies**

   ```bash
   git clone https://github.com/YOUR_USERNAME/prospect-analyzer.git
   cd prospect-analyzer
   pip install -r requirements.txt
   ```

2. **Set your API key**

   ```bash
   cp .env.example .env
   # Edit .env — add your ANTHROPIC_API_KEY
   ```

3. **Create the Managed Agent**

   ```bash
   python setup_agent.py
   ```

   This provisions an agent and environment via the Anthropic API and saves the IDs to `config.json`.

4. **Customize for your use case**

   Edit `industry_config.py` to define what the agent analyzes (see [Configuration Examples](#configuration-examples) below).

5. **Run an analysis**

   ```bash
   python run_analysis.py https://www.example-shop.com
   ```

   Output is saved to `output/{domain}-analysis.md`.

6. **Generate an HTML report**

   ```bash
   python run_analysis.py https://www.example-shop.com --html
   ```

   Or batch-convert all existing analyses:

   ```bash
   python generate_site.py
   ```

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
- **Structured output** with readiness scoring across multiple dimensions

The agent evaluates the target website based on the criteria defined in `industry_config.py`. The default configuration performs a general readiness assessment, but you can customize the system prompt, scoring regex, and report branding for any industry.

### Customizing for your industry

Edit `industry_config.py` to change:
- **SYSTEM_PROMPT** — What the agent analyzes (compliance criteria, scoring rubric)
- **USER_MESSAGE_TEMPLATE** — How the analysis request is phrased
- **REPORT_*_** — HTML report branding (title, subtitle, score label)
- **BRAND_REGEX / SCORE_REGEX** — How to extract metadata from analysis output

## Configuration Examples

Below are two examples showing how to adapt `industry_config.py` for different industries. You only need to override the key variables — everything else uses sensible defaults.

### E-commerce UX Audit

Analyze online stores for usability issues and conversion optimization opportunities.

```python
SYSTEM_PROMPT = """You are a UX and conversion optimization expert.
Evaluate the given e-commerce website across: navigation clarity,
product page completeness, checkout friction, mobile responsiveness,
page load indicators, and trust signals (reviews, security badges).
Score each dimension 1-10 and provide an overall conversion readiness
score...."""

USER_MESSAGE_TEMPLATE = (
    "Analyze this e-commerce store's UX and conversion readiness: {url}\n\n"
    "Browse product pages, attempt the checkout flow, and check mobile layout."
)

REPORT_HEADER_TAG = "UX & Conversion Assessment"
```

### SaaS Security Compliance

Assess a SaaS product's public posture against SOC 2 and ISO 27001 requirements.

```python
SYSTEM_PROMPT = """You are a cybersecurity analyst specializing in
SaaS compliance. Evaluate the target company's public security posture:
trust/security page, SOC 2 Type II report availability, data encryption
mentions, SSO/MFA support, GDPR/DPA documentation, incident response
policy, and subprocessor transparency. Score readiness 1-10...."""

USER_MESSAGE_TEMPLATE = (
    "Evaluate this SaaS product for SOC 2 / ISO 27001 readiness: {url}\n\n"
    "Check their security page, docs, trust center, and terms of service."
)

REPORT_HEADER_TAG = "Security Compliance Assessment"
```

## License

MIT
