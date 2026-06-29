#!/bin/bash
# Push the cavity-ghia-validation repo to GitHub
# Run this script after installing gh CLI or creating the repo manually

REPO_DIR="/home/sorox07/OpenFOAM/sorox07-13/run/cavity-ghia-validation"
REPO_NAME="cavity-ghia-validation"

cd "$REPO_DIR"

echo "=== Pushing to GitHub ==="
echo ""
echo "Option 1: If you have gh CLI installed and authenticated:"
echo "  gh repo create $REPO_NAME --public --source=. --push"
echo ""
echo "Option 2: Manual — create repo on GitHub first, then:"
echo "  git remote add origin git@github.com:soumitd730/$REPO_NAME.git"
echo "  git push -u origin main"
echo ""
echo "Option 3: HTTPS (if no SSH key):"
echo "  git remote add origin https://github.com/soumitd730/$REPO_NAME.git"
echo "  git push -u origin main"
