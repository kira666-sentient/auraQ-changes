import os
import sys

# Initialize with very basic error handling since this is the entry point
try:
    from flask import Flask
    from app import app
    
    # CRITICAL: Export Flask app for Vercel serverless functions
    # This is the correct way for Vercel to import the Flask app
    # app = app must be defined at module level, not inside a function
except Exception as e:
    print(f"Critical error importing app: {str(e)}")
    # Create a minimal Flask app as fallback
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return {
            'error': 'Application initialization failed',
            'details': str(e)
        }, 500

# This is what Vercel's Python serverless runtime looks for
# Both must be defined at module level
application = app
handler = app

# For local development
if __name__ == "__main__":
    app.run(debug=True)