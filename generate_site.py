"""
generate_site.py — Vygeneruje HTML z existujících MD analýz a připraví site/ pro deploy.

Použití:
  python3 generate_site.py              # zpracuje všechny .md z output/
  python3 generate_site.py laklara.md   # zpracuje jen konkrétní soubor
"""

import os
import re
import sys
import shutil
from datetime import datetime
from html_generator import generuj_html, extrahuj_metadata

OUTPUT_DIR = "output"
SITE_DIR = "site"


def zpracuj_analyzu(md_path):
    """Převede jednu MD analýzu na HTML a zkopíruje do site/."""
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Název HTML souboru: www.laklara.cz-analysis.md → laklara.html
    basename = os.path.basename(md_path)
    # Extrahuj doménové jméno
    domain_match = re.match(r"(?:www\.)?(.+?)-analysis\.md$", basename)
    if domain_match:
        slug = domain_match.group(1).replace(".", "-").replace("_", "-")
    else:
        slug = basename.replace(".md", "").replace(".", "-")

    html_filename = f"{slug}.html"
    html_path = os.path.join(SITE_DIR, html_filename)

    generuj_html(md_text, html_path)
    brand, score = extrahuj_metadata(md_text)

    print(f"  {basename} → {html_filename} ({brand}, skóre {score}/10)")
    return {
        "slug": slug,
        "filename": html_filename,
        "brand": brand,
        "score": score,
        "md_file": basename,
    }


def generuj_index(analyzy):
    """Vygeneruje index.html s přehledem všech analýz."""
    datum = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = ""
    for a in sorted(analyzy, key=lambda x: x["brand"]):
        rows += f"""
        <tr>
          <td><a href="{a['filename']}">{a['brand']}</a></td>
          <td>{a['score']}/10</td>
          <td><a href="{a['filename']}">Otevřít</a></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cyrcID Prospect Analyzer — Přehled analýz</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Poppins', sans-serif; background: #eae6dd; color: #221e1a;
    min-height: 100vh; padding: 40px 20px;
  }}
  .container {{
    max-width: 700px; margin: 0 auto; background: #fff;
    border-radius: 8px; overflow: hidden;
    box-shadow: 0 4px 24px rgba(34,30,26,0.1);
  }}
  .header {{
    background: #221e1a; padding: 36px 40px; color: #dcd7ba;
  }}
  .header h1 {{ font-size: 22px; font-weight: 700; color: #fff; }}
  .header p {{ font-size: 13px; margin-top: 6px; color: #b8b49a; }}
  .content {{ padding: 32px 40px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    text-align: left; padding: 10px 12px; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; color: #7a756e;
    border-bottom: 2px solid #eae7e0;
  }}
  td {{
    padding: 14px 12px; border-bottom: 1px solid #eae7e0; font-size: 15px;
  }}
  tr:hover td {{ background: #f5f3ed; }}
  a {{ color: #221e1a; font-weight: 600; text-decoration: none; }}
  a:hover {{ color: #4a7c59; }}
  .meta {{
    padding: 16px 40px; font-size: 12px; color: #b8b49a;
    border-top: 1px solid #eae7e0;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>cyrcID Prospect Analyzer</h1>
    <p>DPP Readiness analýzy fashion e-shopů</p>
  </div>
  <div class="content">
    <table>
      <thead>
        <tr><th>Značka</th><th>DPP Skóre</th><th>Analýza</th></tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>
  <div class="meta">
    Poslední aktualizace: {datum} · Interní nástroj cyrcID
  </div>
</div>
</body>
</html>"""

    index_path = os.path.join(SITE_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  index.html vygenerován ({len(analyzy)} analýz)")


def main():
    os.makedirs(SITE_DIR, exist_ok=True)

    # Zjisti které soubory zpracovat
    if len(sys.argv) > 1:
        md_files = [os.path.join(OUTPUT_DIR, f) for f in sys.argv[1:]]
    else:
        md_files = [
            os.path.join(OUTPUT_DIR, f)
            for f in os.listdir(OUTPUT_DIR)
            if f.endswith("-analysis.md")
        ]

    if not md_files:
        print("Žádné analýzy k zpracování. Nejdřív spusť run_analysis.py.")
        return

    print(f">>> Generuji HTML z {len(md_files)} analýz...")
    analyzy = []
    for md_path in md_files:
        if os.path.exists(md_path):
            analyzy.append(zpracuj_analyzu(md_path))
        else:
            print(f"  VAROVÁNÍ: {md_path} neexistuje, přeskakuji.")

    print(">>> Generuji index.html...")
    generuj_index(analyzy)

    print(f"\n>>> Site připraven v {SITE_DIR}/")
    print(f"    Soubory: index.html + {len(analyzy)} analýz")


if __name__ == "__main__":
    main()
