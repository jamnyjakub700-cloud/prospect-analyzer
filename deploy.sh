#!/bin/bash
# deploy.sh — Zkopíruje HTML analýzy do cyrcid-proposals/output/ a pushne na Netlify.
#
# Cyrcid-proposals repo má Netlify auto-deploy z main branch (publish dir: output/).
# Tento skript kopíruje HTML soubory ze site/ do output/ a pushne.
#
# Použití:
#   ./deploy.sh              # zkopíruje + commitne + pushne

set -euo pipefail
cd "$(dirname "$0")"

SITE_DIR="site"
PROPOSALS_DIR="$HOME/Desktop/claude/cyrcid-proposals"
PROPOSALS_OUTPUT="$PROPOSALS_DIR/output"

# Zkontroluj prerekvizity
if [ ! -d "$SITE_DIR" ] || [ ! -f "$SITE_DIR/index.html" ]; then
    echo "CHYBA: Složka site/ neexistuje. Nejdřív spusť: python3 generate_site.py"
    exit 1
fi

if [ ! -d "$PROPOSALS_DIR/.git" ]; then
    echo "CHYBA: $PROPOSALS_DIR není git repo."
    exit 1
fi

echo "=== cyrcID Prospect Analyzer — Deploy do Netlify ==="
echo ""

# Zkopíruj HTML analýzy (ne index.html — ten je jen interní)
count=0
for html_file in "$SITE_DIR"/*.html; do
    basename=$(basename "$html_file")
    [ "$basename" = "index.html" ] && continue

    # Přejmenuj: laklara-cz.html → laklara-dpp-analysis.html
    slug="${basename%.html}"
    target_name="${slug}-dpp-analysis.html"
    # Pokud už má -dpp-analysis, neměň
    if [[ "$basename" == *-dpp-analysis.html ]]; then
        target_name="$basename"
    fi

    cp "$html_file" "$PROPOSALS_OUTPUT/$target_name"
    echo "  $basename → output/$target_name"
    count=$((count + 1))
done

echo ""
echo ">>> Zkopírováno $count souborů do cyrcid-proposals/output/"

# Commitni a pushni
cd "$PROPOSALS_DIR"
git add output/*-dpp-analysis.html
if git diff --cached --quiet; then
    echo ">>> Žádné změny k commitnutí."
else
    git commit -m "Add DPP analysis: prospect-analyzer outputs ($(date +%Y-%m-%d))"
    echo ">>> Pushing to origin/main..."
    git push origin main
    echo ""
    echo ">>> Deploy spuštěn! Netlify auto-deployne z main branch."
    echo "    Soubory budou dostupné na: https://{tvoje-netlify-url}.netlify.app/"
fi
