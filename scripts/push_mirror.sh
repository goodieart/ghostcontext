#!/usr/bin/env sh
# Push current branch to origin and github remotes.
set -e
branch=$(git rev-parse --abbrev-ref HEAD)
git push origin "$branch"
git push github "$branch"
