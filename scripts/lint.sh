#!/bin/bash

# Code linting script
set -e

echo "🔍 Running code quality checks..."

echo "📋 Running Ruff linting..."
uv run ruff check backend/ main.py

echo "🔍 Running MyPy type checking..."
uv run mypy backend/ main.py

echo "✅ All checks passed!"