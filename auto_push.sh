#!/bin/bash
# auto_push.sh — stage, commit, and push, but ONLY when you run this file.
# Nothing in the project triggers this automatically.
# usage: ./auto_push.sh "your commit message"

msg="${1:-update $(date '+%Y-%m-%d %H:%M:%S')}"
branch=$(git rev-parse --abbrev-ref HEAD)

git add -A
git commit -m "$msg"
git push origin "$branch"
