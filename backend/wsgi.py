"""
Simple WSGI file that imports the main Flask app from app.py
This file is no longer needed for Vercel deployment but kept for local development.
"""
import os
import sys

try:
    # Import the app directly from app.py
    from app import app as application
    app = application
    
except Exception as e:
    import traceback
    from flask import Flask, jsonify
    
    print(f"Error importing app: {str(e)}")
    traceback.print_exc()
    
    # Create a minimal fallback app for diagnostic purposes
    app = Flask(__name__)
    application = app
    # Add diagnostic route to the fallback app
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            'error': 'Application initialization failed',
            'message': str(e)
        }), 500
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
application = app  # WSGI standard 
handler = app      # For AWS Lambda/Vercel

# Define the WSGI callable as "handler" variable.
def handle(event, context):
    return app(event, context)

# For local development
if __name__ == "__main__":
    app.run(debug=True)