#!/bin/bash

REPO_DIR="$HOME/Maggie_AI"
BRANCH="main"

cd "$REPO_DIR" || exit

echo "🚀 Maggie AI Auto-Push Watcher Running..."
echo "Monitoring $REPO_DIR for file updates..."

inotifywait -m -r -e modify,create,delete,move \
  --exclude '(venv/|\.venv/|\.git/|data/|__pycache__/)' \
  "$REPO_DIR" | while read -r directory events filename; do

    echo "⚡ Change detected in $directory$filename ($events)"
    sleep 2

    if [[ -n $(git status --porcelain) ]]; then
        echo "📦 Staging and committing..."
        git add .
        COMMIT_MSG="auto-update: $(date +'%Y-%m-%d %H:%M:%S') - modified $filename"
        git commit -m "$COMMIT_MSG"

        echo "⬆️ Pushing to GitHub..."
        git push origin "$BRANCH"
        echo "✅ Sync complete!"
        echo "------------------------------------------------"
    fi
done
