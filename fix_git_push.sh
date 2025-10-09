#!/bin/bash

echo "Fixing Git push issues..."

# Check current branch
echo "Current branch: $(git branch --show-current)"

# Check remote
echo "Remote repositories:"
git remote -v

# Try to push with verbose output
echo "Attempting to push to origin..."
git push -v origin main

# If push fails, try to reset and force push
if [ $? -ne 0 ]; then
    echo "Push failed, trying to reset and force push..."
    git fetch origin
    git reset --hard origin/main
    git push -v origin main
fi