#!/bin/bash

# Code formatting script
set -e

echo "🔧 Running code formatters..."

echo "📝 Formatting with Black..."
uv run black backend/ main.py

echo "🔍 Formatting with Ruff..."
uv run ruff format backend/ main.py

echo "✅ Code formatting complete!"