#!/bin/bash

echo "Starting build process for AuraQ backend"
echo "Python version:"
python --version

echo "Installing flask_pymongo directly first"
pip install flask_pymongo==2.3.0

echo "Installing dependencies from requirements-vercel.txt"
pip install -r requirements-vercel.txt

echo "Installing NLTK data to /tmp/nltk_data"
# Create NLTK_DATA directory
mkdir -p /tmp/nltk_data

# Set NLTK_DATA environment variable
export NLTK_DATA=/tmp/nltk_data

# Download NLTK resources in Python
python -c "import nltk; nltk.download('punkt', download_dir='/tmp/nltk_data'); nltk.download('averaged_perceptron_tagger', download_dir='/tmp/nltk_data')"

echo "Listing installed packages:"
pip list | grep -E 'flask|pymongo'

echo "Build completed successfully!"