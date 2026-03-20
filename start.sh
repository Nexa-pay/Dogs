#!/bin/bash

echo "🚀 Starting Soul Bot..."

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps

# Run the bot
python soul.py
