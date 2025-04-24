"""
Simple script to run the AuraQ backend server
"""
import os
import sys
import subprocess
import importlib
import platform
import time
import signal
import argparse

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AuraQ Backend Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--production", action="store_true", help="Run in production mode using gunicorn/waitress")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    return parser.parse_args()

def check_dependencies():
    """Check if all required dependencies are installed"""
    # Read requirements from requirements.txt
    req_file_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if not os.path.exists(req_file_path):
        print("Error: requirements.txt file not found.")
        return False
    
    try:
        with open(req_file_path, 'r') as f:
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name without version
                    package_name = line.split('==')[0].split('>=')[0]
                    requirements.append(package_name)
    except Exception as e:
        print(f"Error reading requirements file: {str(e)}")
        return False
    
    # Define critical packages that absolutely must be available
    critical_packages = [
        'flask', 
        'flask_cors', 
        'flask_bcrypt', 
        'flask_jwt_extended',
        'textblob'
    ]
    
    # Optional packages that are nice to have but not essential
    optional_packages = ['nltk', 'gunicorn', 'waitress']
    
    # Mapping from requirement name to import name if they differ
    import_name_map = {
        "python-dotenv": "dotenv",
        "scikit-learn": "sklearn",
        "google-generativeai": "google.generativeai" # Handle multi-part names
        # Add other mappings here if needed
    }
    
    missing_required = []
    missing_critical = []
    missing_optional = []
    
    for package in requirements:
        # Skip optional packages for now
        if package.lower() in [pkg.lower() for pkg in optional_packages]:
            continue
            
        try:
            # Use mapped import name if available, otherwise derive it
            import_name = import_name_map.get(package, package.replace('-', '_').lower())
            importlib.import_module(import_name)
        except ImportError:
            missing_required.append(package)
            if package.lower() in [pkg.lower() for pkg in critical_packages]:
                missing_critical.append(package)
    
    for package in optional_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_optional.append(package)
    
    if missing_optional:
        print(f"Optional dependencies not available: {', '.join(missing_optional)}")
        print("The application will work with reduced functionality.")
    
    if missing_critical:
        print(f"Critical dependencies missing: {', '.join(missing_critical)}")
        return False
        
    if missing_required:
        print(f"Some required dependencies are missing: {', '.join(missing_required)}")
        print("These will be installed automatically.")
        return False
        
    return True

def setup_nltk():
    """Download required NLTK data (optional)"""
    try:
        import nltk
        nltk_data_packages = ['punkt', 'averaged_perceptron_tagger']
        
        print("Setting up NLTK data...")
        for package in nltk_data_packages:
            try:
                nltk.download(package, quiet=True)
                print(f"✓ Downloaded NLTK package: {package}")
            except Exception as e:
                print(f"! Failed to download NLTK package {package}: {str(e)}")
        
        return True
    except ImportError:
        print("NLTK not available - TextBlob will use fallback tokenizers")
        return False
    except Exception as e:
        print(f"Error setting up NLTK: {str(e)} - TextBlob will use fallback tokenizers")
        return False

def setup_environment():
    """Setup environment for the application"""
    # Create routes directory if it doesn't exist
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    if not os.path.exists(routes_dir):
        os.makedirs(routes_dir)
        print(f"Created routes directory at: {routes_dir}")
    
    # Create __init__.py in routes directory if it doesn't exist
    init_file = os.path.join(routes_dir, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("# routes package initialization\n")
        print(f"Created {init_file}")
    
    # Check for database directory
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"Created instance directory for database at: {instance_dir}")
    
    # Look for .env file and create a template if it doesn't exist
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("No .env file found. Creating template...")
        with open(env_file, 'w') as f:
            f.write("# AuraQ Environment Configuration\n")
            f.write("JWT_SECRET_KEY=change_this_to_a_random_secure_key\n")
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            f.write("FLASK_APP=app.py\n")
            f.write("FLASK_ENV=development\n")
        print(f"Created .env template at: {env_file}")
        print("⚠️ Please edit the .env file and fill in your actual API keys and secrets!")

def install_dependencies():
    """Install missing dependencies from requirements.txt"""
    print("Installing dependencies from requirements.txt...")
    
    req_file_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    try:
        # First, upgrade pip itself
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("✓ Upgraded pip")
        
        # Install setuptools first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "setuptools"])
        print("✓ Installed setuptools")
        
        # Install from requirements.txt
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file_path])
        print("✓ Installed dependencies from requirements.txt")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error during dependency installation: {str(e)}")
        return False

def check_db():
    """Verify database exists and is initialized"""
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'aura_detector.db')
    if not os.path.exists(db_path):
        print("Database file not found. It will be created on first run.")

def run_flask_dev(host="127.0.0.1", port=5000, debug=False):
    """Run Flask in development mode"""
    print(f"Starting Flask development server on http://{host}:{port}")
    
    # Set environment variables
    os.environ["FLASK_APP"] = "app.py"
    if debug:
        os.environ["FLASK_DEBUG"] = "1"
    
    try:
        from flask import Flask
        import app  # Import the app module to check for syntax errors
        
        # Use subprocess to run Flask with proper environment
        cmd = [sys.executable, "-m", "flask", "run", f"--host={host}", f"--port={port}"]
        if debug:
            cmd.append("--debug")
        
        # Run Flask in a subprocess that can be terminated
        process = subprocess.Popen(cmd)
        
        try:
            # Wait for the process to finish
            process.wait()
        except KeyboardInterrupt:
            print("\nShutting down Flask server...")
            # Try to terminate gracefully
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                # Force kill if still running
                process.kill()
        
    except ImportError as e:
        print(f"Error importing Flask: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Flask: {str(e)}")
        sys.exit(1)

def run_production_server(host="0.0.0.0", port=5000):
    """Run Flask with a production WSGI server"""
    # Check if gunicorn is available (typically on Unix systems)
    try:
        if platform.system() != "Windows":
            import gunicorn
            print(f"Starting Gunicorn production server on http://{host}:{port}")
            os.system(f"gunicorn --bind {host}:{port} wsgi:app")
            return
    except ImportError:
        pass
    
    # Fallback to waitress (works on Windows)
    try:
        from waitress import serve
        import app
        print(f"Starting Waitress production server on http://{host}:{port}")
        serve(app.app, host=host, port=port)
    except ImportError:
        print("Error: Neither gunicorn nor waitress is available for production server.")
        print("Installing waitress...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "waitress"])
            print("Successfully installed waitress. Restarting...")
            # Try again now that waitress is installed
            from waitress import serve
            import app
            print(f"Starting Waitress production server on http://{host}:{port}")
            serve(app.app, host=host, port=port)
        except Exception as e:
            print(f"Failed to install production server: {str(e)}")
            print("Falling back to development server (not recommended for production)")
            run_flask_dev(host, port)

def setup_signal_handlers():
    """Setup handlers for system signals"""
    def signal_handler(sig, frame):
        print("\nShutting down AuraQ backend server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if platform.system() != "Windows":
        signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    try:
        args = parse_arguments()
    except Exception as e:
        print(f"Error parsing arguments: {str(e)}")
        args = argparse.Namespace(port=5000, host="127.0.0.1", production=False, debug=False)
    
    print("=== AuraQ Backend Setup ===")
    
    setup_environment()
    setup_signal_handlers()
    
    if not check_dependencies():
        print("Some dependencies are missing. Installing them now...")
        if not install_dependencies():
            print("Failed to install all dependencies. Please install them manually:")
            print("Run: pip install -r requirements.txt")
            sys.exit(1)
    
    # Try to download NLTK data but continue even if it fails
    try:
        setup_nltk()
    except Exception as e:
        print(f"Note: NLTK setup failed but that's okay, app will use fallbacks: {str(e)}")
    
    # Verify database exists
    check_db()
    
    print("\n=== Starting AuraQ Backend Server ===")
    
    try:
        if args.production:
            run_production_server(args.host, args.port)
        else:
            run_flask_dev(args.host, args.port, args.debug)
    except Exception as e:
        print(f"Error running the server: {str(e)}")
        sys.exit(1)
