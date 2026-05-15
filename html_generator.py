"""
html_generator.py — Konverze Markdown DPP analýzy do branded HTML.

Vizuální styl převzatý z cyrcID proposal šablony (dpp-proposal-template.html).
Brand barvy z ~/Desktop/claude/E-books/brand.json.
"""

import re
import os
from datetime import datetime


def md_to_html(md_text):
    """Převede Markdown text na HTML sekce pro DPP analýzu.

    Parsuje strukturu analýzy (headingy, tabulky, seznamy, odstavce)
    a obaluje je do cyrcID branded HTML.
    """
    lines = md_text.split("\n")
    html_parts = []
    section_num = 0
    in_table = False
    table_rows = []
    table_headers = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- Horizontální čára ---
        if line.strip() in ("---", "***", "___"):
            if in_table:
                html_parts.append(_render_table(table_headers, table_rows))
                in_table = False
                table_rows = []
                table_headers = []
            i += 1
            continue

        # --- H1: Hlavní nadpis (přeskočíme, je v headeru) ---
        if line.startswith("# ") and not line.startswith("## "):
            i += 1
            continue

        # --- H2: Sekce ---
        if line.startswith("## "):
            if in_table:
                html_parts.append(_render_table(table_headers, table_rows))
                in_table = False
                table_rows = []
                table_headers = []
            section_num += 1
            title = line[3:].strip()
            # Odstraň číslo sekce pokud je (např. "1. Profil značky")
            title = re.sub(r"^\d+\.\s*", "", title)
            html_parts.append(
                f'<div class="section-num">{section_num:02d}</div>\n'
                f'<h2>{_inline_md(title)}</h2>\n'
            )
            i += 1
            continue

        # --- H3: Podsekce ---
        if line.startswith("### "):
            if in_table:
                html_parts.append(_render_table(table_headers, table_rows))
                in_table = False
                table_rows = []
                table_headers = []
            title = line[4:].strip()
            html_parts.append(f'<h3>{_inline_md(title)}</h3>\n')
            i += 1
            continue

        # --- Tabulka ---
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                # První řádek tabulky = hlavička
                table_headers = cells
                in_table = True
                i += 1
                # Přeskoč separator řádek (|---|---|)
                if i < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i].strip()):
                    i += 1
                continue
            else:
                table_rows.append(cells)
                i += 1
                continue

        # Uzavři tabulku pokud další řádek není tabulka
        if in_table and (not line.strip().startswith("|") or "|" not in line):
            html_parts.append(_render_table(table_headers, table_rows))
            in_table = False
            table_rows = []
            table_headers = []

        # --- Seznam (- nebo číslo.) ---
        if re.match(r"^[\-\*]\s", line.strip()) or re.match(r"^\d+\.\s", line.strip()):
            list_items = []
            while i < len(lines):
                l = lines[i].strip()
                if re.match(r"^[\-\*]\s", l):
                    list_items.append(l[2:])
                elif re.match(r"^\d+\.\s", l):
                    list_items.append(re.sub(r"^\d+\.\s", "", l))
                elif l == "":
                    break
                else:
                    break
                i += 1
            items_html = "".join(f'<li>{_inline_md(item)}</li>\n' for item in list_items)
            html_parts.append(f'<ul class="bullet-list">\n{items_html}</ul>\n')
            continue

        # --- Blockquote ---
        if line.strip().startswith("> "):
            quote_text = line.strip()[2:]
            html_parts.append(
                f'<div class="info-box">\n'
                f'<p>{_inline_md(quote_text)}</p>\n'
                f'</div>\n'
            )
            i += 1
            continue

        # --- Odstavec ---
        if line.strip():
            # Sbíráme víceřádkový odstavec
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith("|") and not lines[i].strip().startswith(">") and not re.match(r"^[\-\*]\s", lines[i].strip()) and not re.match(r"^\d+\.\s", lines[i].strip()) and lines[i].strip() not in ("---", "***", "___"):
                para_lines.append(lines[i].strip())
                i += 1
            text = " ".join(para_lines)
            if text:
                html_parts.append(f'<p>{_inline_md(text)}</p>\n')
            continue

        i += 1

    # Uzavři případnou otevřenou tabulku
    if in_table:
        html_parts.append(_render_table(table_headers, table_rows))

    return "\n".join(html_parts)


def _inline_md(text):
    """Převede inline Markdown (bold, italic, code, emoji) na HTML."""
    # Bold **text** nebo __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic *text* nebo _text_
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code `text`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # Odkazy [text](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" target="_blank">\1</a>', text)
    # Status emoji → barevné badge
    text = text.replace("✅", '<span class="badge badge-ok">✅</span>')
    text = text.replace("⚠️", '<span class="badge badge-warn">⚠️</span>')
    text = text.replace("❌", '<span class="badge badge-fail">❌</span>')
    return text


def _render_table(headers, rows):
    """Renderuje HTML tabulku z hlaviček a řádků."""
    if not headers:
        return ""
    th = "".join(f"<th>{_inline_md(h)}</th>" for h in headers)
    tr_list = []
    for row in rows:
        # Doplň prázdné buňky pokud řádek má méně sloupců
        while len(row) < len(headers):
            row.append("")
        cells = "".join(f"<td>{_inline_md(c)}</td>" for c in row)
        tr_list.append(f"<tr>{cells}</tr>")
    trs = "\n".join(tr_list)
    return f"""<div class="table-wrap">
<table>
<thead><tr>{th}</tr></thead>
<tbody>
{trs}
</tbody>
</table>
</div>
"""


def extrahuj_metadata(md_text):
    """Extrahuje název značky a DPP skóre z Markdown analýzy."""
    brand = "Neznámá značka"
    score = "N/A"

    # Název z H1
    m = re.search(r"^#\s+DPP Analýza:\s*(.+)$", md_text, re.MULTILINE)
    if m:
        brand = m.group(1).strip()

    # DPP Readiness skóre
    m = re.search(r"DPP Readiness skóre:\s*\*?\*?(\d+[\.,]?\d*)\s*/\s*10", md_text)
    if m:
        score = m.group(1).replace(",", ".")

    return brand, score


def generuj_html(md_text, output_path):
    """Vygeneruje kompletní HTML soubor z Markdown analýzy."""
    cta_url = os.environ.get("CTA_URL", "https://calendly.com/your-link")
    company_name = os.environ.get("COMPANY_NAME", "YourCompany")
    contact_email = os.environ.get("CONTACT_EMAIL", "hello@example.com")
    company_website = os.environ.get("COMPANY_WEBSITE", "www.example.com")
    brand, score = extrahuj_metadata(md_text)
    body_html = md_to_html(md_text)
    datum = datetime.now().strftime("%-d. %B %Y").replace(
        "January", "ledna").replace("February", "února").replace(
        "March", "března").replace("April", "dubna").replace(
        "May", "května").replace("June", "června").replace(
        "July", "července").replace("August", "srpna").replace(
        "September", "září").replace("October", "října").replace(
        "November", "listopadu").replace("December", "prosince")

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DPP Analýza — {brand} | cyrcID</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --dark: #221e1a;
    --gold: #dcd7ba;
    --gold-dim: #b8b49a;
    --bg: #FFFFFF;
    --bg-warm: #f8f6f1;
    --bg-section: #f5f3ed;
    --text: #221e1a;
    --text-sec: #4a453e;
    --text-light: #7a756e;
    --accent: #dcd7ba;
    --green: #4a7c59;
    --green-bg: #e8f0ea;
    --radius: 6px;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Poppins', sans-serif;
    color: var(--text);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
    background-color: #eae6dd;
    background-image:
      url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E"),
      repeating-linear-gradient(135deg, transparent, transparent 40px, rgba(34,30,26,0.018) 40px, rgba(34,30,26,0.018) 41px),
      radial-gradient(ellipse at 50% 0%, #f0ece4 0%, #e4dfd5 40%, #d8d3c9 100%);
  }}
  body::before, body::after {{
    content: ''; position: fixed; top: 0; bottom: 0; width: 300px; pointer-events: none; z-index: 0;
  }}
  body::before {{ left: 0; background: linear-gradient(to right, rgba(34,30,26,0.03), transparent); }}
  body::after {{ right: 0; background: linear-gradient(to left, rgba(34,30,26,0.03), transparent); }}

  .page {{
    max-width: 860px; margin: 0 auto; background: var(--bg);
    position: relative; z-index: 1;
    box-shadow: 0 0 0 1px rgba(34,30,26,0.06), 0 4px 16px rgba(34,30,26,0.06), 0 12px 40px rgba(34,30,26,0.08);
  }}
  @media (min-width: 900px) {{
    .page {{ margin-top: 40px; margin-bottom: 60px; border-radius: 4px; overflow: hidden; }}
  }}

  /* HEADER */
  .header {{
    background: var(--dark); padding: 48px 56px 52px; position: relative; overflow: hidden;
  }}
  .header::before {{
    content: ''; position: absolute; inset: 0;
    background-image:
      radial-gradient(circle at 85% 20%, rgba(220,215,186,0.06) 0%, transparent 50%),
      repeating-linear-gradient(120deg, transparent, transparent 80px, rgba(220,215,186,0.02) 80px, rgba(220,215,186,0.02) 81px);
    pointer-events: none;
  }}
  .header::after {{
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 4px; background: var(--gold);
  }}
  .header-top {{
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 36px;
  }}
  .header-tag {{
    font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: var(--gold); font-weight: 500;
  }}
  .header-logo {{
    font-size: 22px; font-weight: 700; color: var(--gold); letter-spacing: -0.5px;
  }}
  .header-score {{
    text-align: right;
  }}
  .header-score-label {{
    font-size: 11px; color: var(--gold-dim); letter-spacing: 1px; text-transform: uppercase;
  }}
  .header-score-value {{
    font-size: 32px; font-weight: 700; color: #fff; margin-top: 2px;
  }}
  .header h1 {{
    font-size: 28px; font-weight: 700; color: #fff; line-height: 1.25; letter-spacing: -0.5px;
  }}
  .header-sub {{
    font-size: 14px; color: var(--gold-dim); margin-top: 8px; font-weight: 300;
  }}
  .header-meta {{
    display: flex; gap: 24px; margin-top: 20px; font-size: 12px; color: var(--gold-dim);
  }}

  /* SECTIONS */
  .section {{
    padding: 48px 56px; border-bottom: 1px solid #eae7e0; position: relative;
    opacity: 0; transform: translateY(20px); animation: fadeUp 0.6s ease forwards;
  }}
  .section::before {{
    content: ''; position: absolute; left: 0; top: 20%; bottom: 20%; width: 2px;
    background: linear-gradient(to bottom, transparent, var(--gold), transparent);
    opacity: 0; transition: opacity 0.4s ease;
  }}
  .section:hover::before {{ opacity: 1; }}
  @keyframes fadeUp {{ to {{ opacity: 1; transform: translateY(0); }} }}

  .section-num {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; background: var(--dark); color: var(--gold);
    font-size: 14px; font-weight: 600; border-radius: 50%; margin-bottom: 16px;
  }}
  .section h2 {{
    font-size: 22px; font-weight: 700; color: var(--dark); margin-bottom: 12px; letter-spacing: -0.3px;
  }}
  .section h3 {{
    font-size: 17px; font-weight: 600; color: var(--dark); margin: 28px 0 12px;
  }}
  .section p {{
    font-size: 15px; color: var(--text-sec); margin-bottom: 16px; font-weight: 400;
  }}

  /* TABLES */
  .table-wrap {{ overflow-x: auto; margin: 20px 0; }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 14px;
  }}
  thead {{ background: var(--dark); }}
  th {{
    padding: 12px 16px; color: var(--gold); font-weight: 600; text-align: left;
    font-size: 13px; letter-spacing: 0.5px;
  }}
  td {{
    padding: 12px 16px; border-bottom: 1px solid #eae7e0; color: var(--text-sec);
    vertical-align: top; line-height: 1.5;
  }}
  tbody tr:hover {{ background: var(--bg-section); }}

  /* LISTS */
  .bullet-list {{ list-style: none; padding: 0; }}
  .bullet-list li {{
    position: relative; padding-left: 20px; margin-bottom: 12px;
    font-size: 15px; color: var(--text-sec); line-height: 1.65;
  }}
  .bullet-list li::before {{
    content: ''; position: absolute; left: 0; top: 10px;
    width: 8px; height: 8px; background: var(--gold); border-radius: 50%;
  }}

  /* INFO BOX */
  .info-box {{
    background: var(--bg-section); border-left: 3px solid var(--gold);
    border-radius: 0 var(--radius) var(--radius) 0; padding: 20px 24px; margin: 24px 0;
  }}
  .info-box p {{ font-size: 14px; color: var(--text-sec); margin-bottom: 6px; }}

  /* BADGES */
  .badge {{ font-size: 14px; }}
  .badge-ok {{ color: var(--green); }}
  .badge-warn {{ color: #b8860b; }}
  .badge-fail {{ color: #c0392b; }}

  code {{
    background: var(--bg-section); padding: 2px 6px; border-radius: 3px;
    font-size: 13px; font-family: 'Courier New', monospace;
  }}
  a {{ color: var(--text-light); transition: color 0.2s; }}
  a:hover {{ color: var(--dark); }}

  /* CTA SECTION */
  .cta-section {{
    background: var(--bg-section); padding: 48px 56px; text-align: center;
    border-bottom: 1px solid #eae7e0;
  }}
  .cta-section h3 {{
    font-size: 20px; font-weight: 700; color: var(--dark); margin-bottom: 12px;
  }}
  .cta-section p {{
    font-size: 15px; color: var(--text-sec); margin-bottom: 24px; max-width: 560px; margin-left: auto; margin-right: auto;
  }}
  .cta-btn {{
    display: inline-block; background: var(--dark); color: var(--gold);
    padding: 14px 32px; border-radius: var(--radius); text-decoration: none;
    font-weight: 600; font-size: 15px; transition: all 0.2s;
  }}
  .cta-btn:hover {{ background: #393530; color: #fff; }}

  /* FOOTER */
  .footer {{
    background: var(--dark); padding: 36px 56px; position: relative; overflow: hidden;
  }}
  .footer::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--gold); z-index: 1;
  }}
  .footer-inner {{
    display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1;
  }}
  .footer-logo {{ font-size: 18px; font-weight: 700; color: var(--gold); }}
  .footer-links {{
    display: flex; gap: 24px; font-size: 13px;
  }}
  .footer-links a {{ color: var(--gold-dim); text-decoration: none; }}
  .footer-links a:hover {{ color: #fff; }}

  /* PRINT */
  @media print {{
    body {{ background: #fff; }}
    body::before, body::after {{ display: none; }}
    .page {{ max-width: 100%; box-shadow: none; margin: 0; }}
    .section {{ opacity: 1; transform: none; animation: none; }}
    .section::before {{ display: none; }}
    .cta-section {{ display: none; }}
  }}

  /* RESPONSIVE */
  @media (max-width: 640px) {{
    .header, .section, .footer, .cta-section {{ padding: 32px 24px; }}
    .header h1 {{ font-size: 22px; }}
    .header-top {{ flex-direction: column; gap: 16px; }}
    .header-score {{ text-align: left; }}
    body::before, body::after {{ display: none; }}
    .section::before {{ display: none; }}
    .footer-inner {{ flex-direction: column; gap: 12px; text-align: center; }}
  }}
</style>
</head>
<body>

<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div class="header-top">
      <div>
        <div class="header-logo">cyrcID</div>
        <div class="header-tag">DPP Readiness Analysis</div>
      </div>
      <div class="header-score">
        <div class="header-score-label">DPP Readiness</div>
        <div class="header-score-value">{score}/10</div>
      </div>
    </div>
    <h1>DPP Analýza: {brand}</h1>
    <div class="header-sub">Digital Product Passport readiness podle ESPR pro textilní průmysl</div>
    <div class="header-meta">
      <span>{datum}</span>
      <span>Zpracoval: cyrcID Prospect Analyzer</span>
    </div>
  </div>

  <!-- CONTENT -->
  <div class="section" style="animation-delay: 0.1s;">
    {body_html}
  </div>

  <!-- CTA -->
  <div class="cta-section">
    <h3>Chcete se dozvědět víc o DPP připravenosti vašeho brandu?</h3>
    <p>Zarezervujte si bezplatnou 20minutovou konzultaci. Ukážeme vám, jak se připravit na povinný digitální produktový pas a co konkrétně musíte udělat.</p>
    <a class="cta-btn" href="{cta_url}" target="_blank">Zarezervovat konzultaci &rarr;</a>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-inner">
      <div class="footer-logo">{company_name}</div>
      <div class="footer-links">
        <a href="mailto:{contact_email}">{contact_email}</a>
        <a href="https://{company_website}" target="_blank">{company_website}</a>
      </div>
    </div>
  </div>

</div>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
