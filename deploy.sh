#!/bin/bash
# deploy.sh — Copy HTML analyses to your hosting repo and push.
#
# Set PROPOSALS_DIR to the path of your Netlify/hosting git repo.
# This script copies HTML files from site/ to the output dir and pushes.
#
# Usage:
#   ./deploy.sh              # copy + commit + push

set -euo pipefail
cd "$(dirname "$0")"

SITE_DIR="site"
PROPOSALS_DIR="${PROPOSALS_DIR:-$HOME/proposals}"
PROPOSALS_OUTPUT="$PROPOSALS_DIR/output"
DEPLOY_SUFFIX="${DEPLOY_SUFFIX:--analysis}"

# Check prerequisites
if [ ! -d "$SITE_DIR" ] || [ ! -f "$SITE_DIR/index.html" ]; then
    echo "ERROR: site/ directory does not exist. First run: python3 generate_site.py"
    exit 1
fi

if [ ! -d "$PROPOSALS_DIR/.git" ]; then
    echo "ERROR: $PROPOSALS_DIR is not a git repo."
    exit 1
fi

echo "=== Prospect Analyzer — Deploy ==="
echo ""

# Copy HTML analyses (not index.html — that's internal only)
count=0
for html_file in "$SITE_DIR"/*.html; do
    basename=$(basename "$html_file")
    [ "$basename" = "index.html" ] && continue

    slug="${basename%.html}"
    target_name="${slug}${DEPLOY_SUFFIX}.html"
    # If already has the suffix, don't change
    if [[ "$basename" == *${DEPLOY_SUFFIX}.html ]]; then
        target_name="$basename"
    fi

    cp "$html_file" "$PROPOSALS_OUTPUT/$target_name"
    echo "  $basename -> output/$target_name"
    count=$((count + 1))
done

echo ""
echo ">>> Copied $count files to output/"

# Commit and push
cd "$PROPOSALS_DIR"
git add output/*${DEPLOY_SUFFIX}.html
if git diff --cached --quiet; then
    echo ">>> No changes to commit."
else
    git commit -m "Add analysis: prospect-analyzer outputs ($(date +%Y-%m-%d))"
    echo ">>> Pushing to origin/main..."
    git push origin main
    echo ""
    echo ">>> Deploy triggered! Files will be available after auto-deploy."
fi
