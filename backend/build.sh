#!/bin/bash

echo "Starting optimized build process for AuraQ backend"
echo "Python version:"
python --version

echo "Installing minimal dependencies for Vercel deployment"
pip install --no-cache-dir -r requirements-vercel.txt

echo "Cleaning up unnecessary files to reduce deployment size"
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

echo "Build completed successfully!"