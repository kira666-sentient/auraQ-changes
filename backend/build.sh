#!/bin/bash

echo "Starting optimized build process for AuraQ backend"
echo "Python version:"
python --version

echo "Installing minimal dependencies for Vercel deployment"
pip install --no-cache-dir -r requirements-vercel.txt

echo "Installing minimal NLTK data (only essential components)"
# Create NLTK_DATA directory
mkdir -p /tmp/nltk_data

# Set NLTK_DATA environment variable
export NLTK_DATA=/tmp/nltk_data

# Only download the specific NLTK resources needed, avoid downloading unnecessary data
python -c "import nltk; nltk.download('punkt', download_dir='/tmp/nltk_data')"

echo "Cleaning up unnecessary files to reduce deployment size"
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

echo "Build completed successfully!"