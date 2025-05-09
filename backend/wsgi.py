import os
import sys
import traceback
import json

# Initialize with very basic error handling since this is the entry point
try:
    from flask import Flask, jsonify
    from app import app
    
    # Add a diagnostic endpoint to help with troubleshooting
    @app.route('/_vercel/debug', methods=['GET'])
    def debug_info():
        """Diagnostic endpoint for troubleshooting Vercel deployment"""
        info = {
            'environment': {
                'VERCEL': os.environ.get('VERCEL', 'Not set'),
                'NLTK_DATA': os.environ.get('NLTK_DATA', 'Not set'),
                'MONGODB_URI_SET': bool(os.environ.get('MONGODB_URI')),
                'GEMINI_API_KEY_SET': bool(os.environ.get('GEMINI_API_KEY')),
                'PATH': os.environ.get('PATH', 'Not set'),
                'PYTHON_VERSION': sys.version
            },
            'filesystem': {
                'tmp_writable': os.access('/tmp', os.W_OK),
                'nltk_data_exists': os.path.exists('/tmp/nltk_data') if os.environ.get('NLTK_DATA') == '/tmp/nltk_data' else False
            }
        }
        return jsonify(info)
    
    # CRITICAL: Export Flask app for Vercel serverless functions
    # This is the correct way for Vercel to import the Flask app
    # app = app must be defined at module level, not inside a function
except Exception as e:
    print(f"Critical error importing app: {str(e)}")
    traceback.print_exc()
    # Create a minimal Flask app as fallback
    from flask import Flask, jsonify, request
    app = Flask(__name__)
    
    error_details = {
        'error': str(e),
        'traceback': traceback.format_exc()
    }
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            'error': 'Application initialization failed',
            'details': error_details
        }), 500
    
    @app.route('/_vercel/debug', methods=['GET'])
    def debug_info():
        """Emergency diagnostic endpoint for troubleshooting Vercel deployment"""
        info = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'environment': {
                'VERCEL': os.environ.get('VERCEL', 'Not set'),
                'NLTK_DATA': os.environ.get('NLTK_DATA', 'Not set'),
                'MONGODB_URI_SET': bool(os.environ.get('MONGODB_URI')),
                'PATH': os.environ.get('PATH', 'Not set'),
                'PYTHON_VERSION': sys.version
            },
            'request': {
                'headers': dict(request.headers),
                'url': request.url,
                'method': request.method
            }
        }
        return jsonify(info)

# This is what Vercel's Python serverless runtime looks for
# Both must be defined at module level
application = app
handler = app

# For local development
if __name__ == "__main__":
    app.run(debug=True)