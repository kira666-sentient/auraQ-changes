from flask import Flask, request, jsonify
from ai_analysis import analyze_mood
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
import os
import sys
import logging
import traceback
from dotenv import load_dotenv
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import time
import pymongo
import json

# Load environment variables from .env file
load_dotenv()

# Configure logger for Vercel environment (console only)
logger = logging.getLogger("aura_q")
logger.setLevel(logging.INFO)

# Prevent duplicate logs by checking if handlers already exist
if not logger.handlers:
    # Create console handler for Vercel
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to the logger
    logger.addHandler(console_handler)
else:
    # If handlers exist, we're probably being imported multiple times
    logger.debug("Logger already configured, skipping handler setup")

# Initialize app
app = Flask(__name__)
logger.info("Starting AuraQ backend application")

# Only log the full startup message once
if not getattr(app, '_startup_complete', False):
    logger.info("Initializing application for the first time")
    app._startup_complete = True

# Configure Flask to avoid trying to write to the filesystem on Vercel
if "VERCEL" in os.environ:
    logger.info("Running in Vercel environment - setting instance_path to /tmp")
    app.instance_path = "/tmp"  # Use /tmp which is writable in Vercel

# MongoDB Configuration with retry logic
db_username = os.environ.get("db_username") # Changed to lowercase
db_password = os.environ.get("db_password") # Changed to lowercase
mongo_uri = None

if db_username and db_password:
    # For robust encoding, consider: from urllib.parse import quote_plus
    # db_password_encoded = quote_plus(db_password)
    mongo_uri = f"mongodb+srv://{db_username}:{db_password}@cluster0.g4j7ljt.mongodb.net/auraQ?retryWrites=true&w=majority&appName=Cluster0"
    logger.info("MONGODB_URI constructed from db_username and db_password environment variables.")
elif os.environ.get("MONGODB_URI"): # Fallback to MONGODB_URI if explicitly set
    mongo_uri = os.environ.get("MONGODB_URI")
    logger.info("Using MONGODB_URI environment variable as db_username/db_password were not found.")
else:
    logger.warning("Neither db_username/db_password nor MONGODB_URI environment variables were found. Using a default local URI that will likely fail in production.")
    mongo_uri = "mongodb://localhost:27017/auraQ"

# Initialize db as None first
db = None
mongo = None

# Function to establish MongoDB connection with retries
def initialize_mongodb_connection(max_retries=3, retry_delay=2):
    global mongo, db
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting MongoDB connection (attempt {retry_count+1}/{max_retries})")
            app.config["MONGO_URI"] = mongo_uri
            
            # Set MongoDB connection options with timeouts
            app.config["MONGO_OPTIONS"] = {  # Corrected indentation for this block
                "serverSelectionTimeoutMS": 5000,
                "connectTimeoutMS": 5000,
                "socketTimeoutMS": 10000
            }
            
            mongo = PyMongo(app)
            db = mongo.db
            
            # Test MongoDB connection
            db.command("ping")
            logger.info("MongoDB connection established and tested successfully")
            return True
            
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            logger.warning(f"MongoDB connection attempt {retry_count} failed: {str(e)}")
            
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    logger.error(f"All MongoDB connection attempts failed. Last error: {last_error}")
    logger.error(traceback.format_exc())
    return False

# Try to establish MongoDB connection
mongodb_connected = initialize_mongodb_connection()

if not mongodb_connected:
    logger.warning("MongoDB connection failed. App will run with limited functionality.")
    # In Vercel we'll continue even with failed MongoDB to allow diagnosis

# Set up CORS for all routes with appropriate origins
FRONTEND_ORIGINS = [
    "http://127.0.0.1:3001",  # Added for Vercel dev frontend
    "http://localhost:3001",   # Added for Vercel dev frontend
    "http://127.0.0.1:3000",  # Backend URL
    "http://localhost:3000",   # Backend URL
    "http://127.0.0.1:5500",  # VS Code Live Server default
    "http://localhost:5500",
    "http://127.0.0.1:5501",  # Alternate port
    "http://localhost:5501",
    "http://127.0.0.1:8080",  # Common dev server port
    "http://localhost:8080",
    "null",  # For file:// protocol
    "http://localhost:*",     # Any localhost port
    "http://127.0.0.1:*"      # Any 127.0.0.1 port
]

# Check environment variable for production frontend URL
if os.environ.get("FRONTEND_URL"):
    FRONTEND_ORIGINS.append(os.environ.get("FRONTEND_URL"))
    logger.info(f"Added production frontend URL: {os.environ.get('FRONTEND_URL')}")

# Configure CORS with more permissive settings for development
CORS(app, resources={
    r"/*": {
        "origins": FRONTEND_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True
    },
})
logger.info(f"CORS configured with origins: {FRONTEND_ORIGINS}")

bcrypt = Bcrypt(app)

# Debug endpoint to list users
@app.route("/debug/users", methods=["GET"])
def debug_list_users():
    response = {
        "mongodb_users": []
    }
    
    # Get MongoDB users if connected
    if mongodb_connected:
        try:
            mongo_users = list(db.users.find({}, {"username": 1, "email": 1, "last_login": 1, "_id": 0}))
            response["mongodb_users"] = mongo_users
            for user in response["mongodb_users"]:
                if "last_login" in user and user["last_login"]:
                    user["last_login"] = user["last_login"].isoformat()
            response["mongodb_count"] = len(response["mongodb_users"])
            response["database_status"] = "Connected"
        except Exception as e:
            response["mongodb_error"] = str(e)
            response["database_status"] = "Error"
    else:
        response["database_status"] = "Not connected"
    
    return jsonify(response)

# Secret key for JWT (loaded from environment variables)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "supersecretkey")
if app.config["JWT_SECRET_KEY"] == "supersecretkey":
    logger.warning("WARNING: SECURITY RISK: Using default JWT secret key - this is not secure for production!")
    logger.warning("Please set the JWT_SECRET_KEY environment variable with a secure random key")
    logger.warning("You can generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")

# Configure JWT token expiration
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # 24 hours - using timedelta for Flask 2.3.x
jwt = JWTManager(app)

# Custom error handler class
class ApiError(Exception):
    """Base class for API errors with status code and message"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        result = dict(self.payload or {})
        result['error'] = self.message
        return result

@app.errorhandler(ApiError)
def handle_api_error(error):
    logger.error(f"API Error: {error.message} - Code: {error.status_code}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.errorhandler(Exception)
def handle_generic_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def handle_404_error(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "ok", "message": "AuraQ backend is running"}), 200

@app.route("/signup", methods=["POST"])
def json_signup():
    try:
        # Check MongoDB connection first
        if not mongodb_connected:
            logger.error("MongoDB connection not available for registration")
            return jsonify({"error": "Database connection error"}), 503
        
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password are required"}), 400
        
        username = data['username']
        password = data['password']
        email = data.get('email', f"{username}@example.com")  # Default email if not provided
        
        # Check if username already exists in MongoDB
        if db.users.find_one({"username": username}):
            return jsonify({"error": "Username already exists"}), 409
        
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create new user
        new_user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "rewards": 5,
            "daily_count": 0,
            "last_reset_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Insert into MongoDB
        result = db.users.insert_one(new_user)
        logger.info(f"User {username} registered successfully in MongoDB")
        
        # Create token for auto-login
        access_token = create_access_token(identity=username)
        
        return jsonify({
            "message": "User registered successfully", 
            "token": access_token,
            "username": username
        }), 201
        
    except Exception as e:
        logger.error(f"Unexpected error during signup: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Registration error", "details": str(e)}), 500

@app.route("/login", methods=["POST"])
def json_login():
    try:
        data = request.get_json()
        
        logger.info(f"Login attempt for username: {data.get('username', 'unknown')}")
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password are required"}), 400
        
        username = data['username']
        password = data['password']
        
        # MongoDB authentication only
        if not mongodb_connected:
            logger.error("MongoDB connection not available for authentication")
            return jsonify({"error": "Database connection error"}), 503
            
        try:
            user = db.users.find_one({"username": username})
            
            # Check if user exists and password matches
            if not user:
                logger.warning(f"User {username} not found in MongoDB")
                return jsonify({"error": "Invalid username or password"}), 401
                
            if not bcrypt.check_password_hash(user["password"], password):
                logger.warning(f"Invalid password for user: {username}")
                return jsonify({"error": "Invalid username or password"}), 401
                
            logger.info(f"MongoDB authentication successful for user: {username}")
            
            # Update user's last login timestamp
            current_time = datetime.utcnow()
            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {"last_login": current_time},
                    "$inc": {"login_count": 1}
                }
            )
            
            # Create access token
            access_token = create_access_token(identity=username)
            
            return jsonify({
                "message": "Login successful",
                "token": access_token,
                "username": username
            }), 200
                
        except Exception as e:
            logger.error(f"MongoDB authentication error: {str(e)}")
            return jsonify({"error": "Authentication error", "details": str(e)}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error during JSON login: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Authentication error", "details": str(e)}), 500

# Helper function to check if MongoDB is available
def check_db_connection():
    if db is None:
        raise ApiError("Database connection not established", 503)
    
    try:
        # Quick ping to check connection
        db.command("ping")
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise ApiError("Database connection error", 503)

# Helper function to serialize MongoDB ObjectId
def serialize_objectid(obj_id):
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    return obj_id

# Endpoint for user registration
@app.route("/auth/register", methods=["POST"])
def register():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        data = request.get_json()
        
        # Log attempt with username but no other sensitive data
        logger.info(f"Registration attempt for username: {data.get('username', 'unknown')}")
        
        # Validate required fields
        if not data or not all(k in data for k in ["username", "email", "password"]):
            raise ApiError("Missing required fields", 400)
        
        # Check if username or email already exists
        if db.users.find_one({"username": data["username"]}):
            logger.info(f"Registration failed: username {data['username']} already exists")
            raise ApiError("Username already exists", 409)
        
        if db.users.find_one({"email": data["email"]}):
            logger.info(f"Registration failed: email {data['email']} already exists")
            raise ApiError("Email already exists", 409)
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
        
        # Create new user
        new_user = {
            "username": data["username"],
            "email": data["email"],
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "rewards": 5,
            "daily_count": 0,
            "last_reset_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        result = db.users.insert_one(new_user)
        logger.info(f"User {data['username']} registered successfully")
        
        # Generate access token
        access_token = create_access_token(identity=new_user["username"])
        
        return jsonify({
            "message": "User registered successfully",
            "token": access_token,
            "username": new_user["username"]
        }), 201
        
    except ApiError as e:
        # ApiError is already logged and will be handled by the errorhandler
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in user registration: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# Endpoint for user login
@app.route("/auth/login", methods=["POST"])
def login():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        data = request.get_json()
        
        logger.info(f"Login attempt for username: {data.get('username', 'unknown')}")
        
        # Validate required fields
        if not data or not all(k in data for k in ["username", "password"]):
            raise ApiError("Missing required fields", 400)
        
        # Find user by username
        user = db.users.find_one({"username": data["username"]})
        
        # Verify user and password
        if not user or not bcrypt.check_password_hash(user["password"], data["password"]):
            logger.warning(f"Failed login attempt for username: {data.get('username', 'unknown')}")
            # Use same error message to prevent username enumeration
            raise ApiError("Invalid username or password", 401)
        
        # Update user's last login timestamp
        current_time = datetime.utcnow()
        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {"last_login": current_time},
                "$inc": {"login_count": 1}
            }
        )
        
        logger.info(f"Successful login for user: {user['username']}")
        
        # Generate access token
        access_token = create_access_token(identity=user["username"])
        
        return jsonify({
            "message": "Login successful",
            "token": access_token,
            "username": user["username"]
        }), 200
        
    except ApiError:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# Replace print debugging with logger calls
@app.route("/analyze", methods=["POST"])
@jwt_required()  # Enable JWT requirement for authentication
def analyze():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        # Get current user from JWT token
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        logger.debug(f"Received Data: {data}")  # Use logger instead of print

        if not data or "story" not in data:
            return jsonify({"error": "No story provided"}), 400

        story = data["story"].strip()
        if not story:
            return jsonify({"error": "Story cannot be empty"}), 400

        # Get mood and feedback using the analyze_mood function
        mood_feedback = analyze_mood(story)

        logger.debug(f"Mood: {mood_feedback['mood']}, Feedback: {mood_feedback['feedback']}")  # Use logger instead of print

        if mood_feedback["mood"] == "Unknown":
            return jsonify({"error": "Failed to analyze mood"}), 500
            
        # Store only the mood (not the story or feedback)
        new_entry = {
            "user_id": user["_id"],
            "mood": mood_feedback["mood"],
            "timestamp": datetime.utcnow()
        }
        
        # Add to database
        result = db.mood_entries.insert_one(new_entry)
        
        # Include the entry ID in the response
        mood_feedback["id"] = str(result.inserted_id)
        
        return jsonify(mood_feedback)  # Return the mood and feedback to the client

    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")  # Use logger instead of print
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/history", methods=["GET"])
@jwt_required()  # Require authentication
def user_history():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        # Get current user from JWT token
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get query parameters
        limit = request.args.get("limit", default=None, type=int)
        sort = request.args.get("sort", default="desc", type=str)
        
        # Query mood entries
        sort_direction = -1 if sort.lower() == "desc" else 1
        query = {"user_id": user["_id"]}
        
        # Apply sorting and limit
        cursor = db.mood_entries.find(query).sort("timestamp", sort_direction)
        
        # Apply limit if specified
        if limit is not None and isinstance(limit, int) and limit > 0:
            cursor = cursor.limit(limit)
        
        # Get entries and transform to dict format
        history = []
        for entry in cursor:
            history.append({
                "id": str(entry["_id"]),
                "mood": entry["mood"],
                "timestamp": entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"]
            })
        
        return jsonify({"history": history})
        
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in user_history endpoint: {str(e)}")  # Replace print with logger
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/statistics", methods=["GET"])
@jwt_required()
def user_statistics():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        # Get current user from JWT token
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get all mood entries for this user
        entries = list(db.mood_entries.find({"user_id": user["_id"]}))
        
        # Count occurrences of each mood
        mood_counts = {}
        for entry in entries:
            mood = entry["mood"]
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        # Get recent entries
        recent_entries = list(db.mood_entries.find({"user_id": user["_id"]})
                            .sort("timestamp", -1)
                            .limit(5))
        recent_moods = [entry["mood"] for entry in recent_entries]
        
        return jsonify({
            "total_entries": len(entries),
            "mood_counts": mood_counts,
            "recent_moods": recent_moods
        })
        
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in user_statistics endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/history/<entry_id>", methods=["DELETE"])
@jwt_required()
def delete_history_entry(entry_id):
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        # Get current user from JWT token
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Find and delete the entry
        try:
            object_id = ObjectId(entry_id)
        except:
            return jsonify({"error": "Invalid entry ID"}), 400
            
        # Delete the entry if it belongs to the user
        result = db.mood_entries.delete_one({
            "_id": object_id,
            "user_id": user["_id"]
        })
        
        if result.deleted_count == 0:
            return jsonify({"error": "Entry not found"}), 404
        
        return jsonify({"message": "Entry deleted successfully"}), 200
        
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in delete_history_entry endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/history", methods=["DELETE"])
@jwt_required()
def clear_history():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        # Get current user from JWT token
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete all entries for this user
        result = db.mood_entries.delete_many({"user_id": user["_id"]})
        
        return jsonify({
            "message": "History cleared successfully", 
            "count": result.deleted_count
        }), 200
        
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in clear_history endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# Add a health check endpoint for Vercel
@app.route("/debug/login", methods=["POST"])
def debug_login():
    """Debug endpoint that always succeeds login"""
    try:
        data = request.get_json()
        username = data.get('username', 'debug_user')
        
        logger.info(f"Debug login for user: {username}")
        
        # Create access token
        access_token = create_access_token(identity=username)
        
        return jsonify({
            "message": "Debug login successful",
            "token": access_token,
            "username": username
        }), 200
    except Exception as e:
        logger.error(f"Error in debug login: {str(e)}")
        return jsonify({"error": "Debug login failed", "details": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring deployment status"""
    response = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "Vercel" if "VERCEL" in os.environ else "Development",
        "services": {
            "database": "Unknown"
        }
    }
    
    # Check database connectivity - but don't fail if it doesn't work
    try:
        # Use a lightweight query to check MongoDB connection
        try:
            if db is not None:
                db.command("ping")
                response["services"]["database"] = "Connected"
            else:
                response["services"]["database"] = "Not initialized"
        except Exception as e:
            response["services"]["database"] = f"Error: {str(e)[:100]}..."
    except Exception as e:
        response["services"]["database"] = f"Check failed: {str(e)[:100]}..."
    
    return jsonify(response), 200

# Add routes for user rewards
@app.route("/user/rewards", methods=["GET"])
@jwt_required()
def get_rewards():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if reset is needed
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("last_reset_date") != today:
            # Update the user document with reset values
            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "daily_count": 0,
                        "last_reset_date": today,
                        "rewards": 5  # Reset daily rewards to full allowance
                    }
                }
            )
            
            # Get updated user data
            user = db.users.find_one({"_id": user["_id"]})
            
        return jsonify({
            "rewards": user.get("rewards", 0),
            "daily_count": user.get("daily_count", 0)
        }), 200
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in get_rewards endpoint: {str(e)}")
        return jsonify({"error": "Failed to get user rewards", "details": str(e)}), 500

@app.route("/user/rewards", methods=["PUT"])
@jwt_required()
def update_rewards():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        
        if not data or "rewards" not in data:
            return jsonify({"error": "No rewards value provided"}), 400
            
        try:
            new_rewards = int(data["rewards"])
            if new_rewards < 0:
                new_rewards = 0
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid rewards value"}), 400
        
        # Update rewards
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"rewards": new_rewards}}
        )
        
        return jsonify({
            "message": "Rewards updated successfully",
            "rewards": new_rewards
        }), 200
            
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in update_rewards endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/daily-count", methods=["POST"])
@jwt_required()
def increment_daily_count():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if reset is needed
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("last_reset_date") != today:
            # First entry of the day
            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "daily_count": 1,
                        "last_reset_date": today
                    }
                }
            )
            daily_count = 1
        else:
            # Increment daily count
            result = db.users.update_one(
                {"_id": user["_id"]},
                {"$inc": {"daily_count": 1}}
            )
            
            # Get the updated count
            updated_user = db.users.find_one({"_id": user["_id"]})
            daily_count = updated_user.get("daily_count", 0)
        
        return jsonify({
            "message": "Daily count incremented",
            "daily_count": daily_count
        }), 200
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in increment_daily_count endpoint: {str(e)}")
        return jsonify({"error": "Failed to increment daily count", "details": str(e)}), 500

# Weekly mood endpoints
@app.route("/user/weekly-mood", methods=["POST"])
@jwt_required()
def add_weekly_mood():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        
        if not data or "mood" not in data:
            return jsonify({"error": "No mood data provided"}), 400
        
        # Create new weekly mood entry
        new_weekly_mood = {
            "user_id": user["_id"],
            "mood": data["mood"],
            # Use the day index sent from the frontend to ensure correct day of week
            # This is more reliable than trying to convert UTC dates
            "dayIndex": data.get("dayIndex", datetime.now().weekday()),
            "date": datetime.now() if "date" not in data else datetime.fromisoformat(data["date"].replace('Z', '+00:00'))
        }
        
        # Add to database
        result = db.weekly_moods.insert_one(new_weekly_mood)
        
        return jsonify({
            "message": "Weekly mood data saved successfully",
            "id": str(result.inserted_id)
        }), 200
            
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in add_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/user/weekly-mood", methods=["GET"])
@jwt_required()
def get_weekly_mood():
    try:
        # Check MongoDB connection first
        check_db_connection()
        
        username = get_jwt_identity()
        user = db.users.find_one({"username": username})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get entries from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        weekly_entries = list(db.weekly_moods.find({
            "user_id": user["_id"],
            "date": {"$gte": thirty_days_ago}
        }).sort("date", -1))
        
        # Convert to dict format with serialized ids and dates
        weekly_data = []
        logger.info(f"Processing {len(weekly_entries)} weekly mood entries for user {username}")
        for entry in weekly_entries:
            # Ensure we have a dayIndex, if it's missing calculate it from the date
            # But prioritize the dayIndex saved with the entry
            if "dayIndex" in entry:
                day_index = entry["dayIndex"]
            else:
                # Calculate day index from date, but be cautious about timezone issues
                entry_date = entry["date"] if isinstance(entry["date"], datetime) else datetime.fromisoformat(str(entry["date"]).replace('Z', '+00:00'))
                # Use weekday() + 1 % 7 to convert from Python's weekday() (0=Monday) to JS getDay() (0=Sunday)
                day_of_week = entry_date.weekday() if entry_date else datetime.now().weekday()
                day_index = (day_of_week + 1) % 7
            
            entry_data = {
                "id": str(entry["_id"]),
                "mood": entry["mood"],
                "dayIndex": day_index,
                "date": entry["date"].isoformat() if isinstance(entry["date"], datetime) else entry["date"]
            }
            
            # Log each entry's day info for debugging
            logger.info(f"Mood entry: {entry_data['mood']} on day index {day_index}, date: {entry_data['date']}")
            
            weekly_data.append(entry_data)
        
        return jsonify({"weekly_data": weekly_data}), 200
        
    except ApiError as e:
        # Let the global handler take care of this
        raise
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {str(e)}")
        return jsonify({"error": "Database connection error", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"Error in get_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

        logger.error(f"Error in get_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

application = app  # Expose Flask app for Vercel and other WSGI servers

if __name__ == "__main__":
    # This block is for local development only
    # Vercel will use the 'application' object defined above
    app.run(debug=True)

# Removed the explicit 'handler = app' and 'def handle(event, context):'
# as @vercel/python should pick up the WSGI 'application' object directly.
