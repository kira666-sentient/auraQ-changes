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

# Load environment variables from .env file
load_dotenv()

# Configure logger for Vercel environment (console only)
logger = logging.getLogger("aura_q")
logger.setLevel(logging.INFO)

# Create console handler for Vercel
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handler to the logger
logger.addHandler(console_handler)

# Initialize app
app = Flask(__name__)
logger.info("Starting AuraQ backend application")

# Configure Flask to avoid trying to write to the filesystem on Vercel
if "VERCEL" in os.environ:
    logger.info("Running in Vercel environment - setting instance_path to /tmp")
    app.instance_path = "/tmp"  # Use /tmp which is writable in Vercel

# MongoDB Configuration
mongo_uri = os.environ.get("MONGODB_URI")

if not mongo_uri:
    logger.warning("MONGODB_URI not found - using a default URI that will likely fail")
    mongo_uri = "mongodb://localhost:27017/auraQ"

try:
    app.config["MONGO_URI"] = mongo_uri
    mongo = PyMongo(app)
    db = mongo.db
    logger.info("MongoDB connection initialized successfully")
    
    # Test MongoDB connection
    db.command("ping")
    logger.info("MongoDB connection test successful")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")
    logger.error(traceback.format_exc())

# Set up CORS for all routes with appropriate origins
FRONTEND_ORIGINS = [
    "http://127.0.0.1:5500",  # VS Code Live Server default
    "http://localhost:5500",
    "http://127.0.0.1:5501",  # Alternate port
    "http://localhost:5501",
    "http://127.0.0.1:8080",  # Common dev server port
    "http://localhost:8080",
    "null"  # For file:// protocol
]

# Check environment variable for production frontend URL
if os.environ.get("FRONTEND_URL"):
    FRONTEND_ORIGINS.append(os.environ.get("FRONTEND_URL"))
    logger.info(f"Added production frontend URL: {os.environ.get('FRONTEND_URL')}")

# Configure CORS with more permissive settings for development
CORS(app, resources={
    r"/*": {"origins": FRONTEND_ORIGINS},
})
logger.info(f"CORS configured with origins: {FRONTEND_ORIGINS}")

bcrypt = Bcrypt(app)

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

# Helper function to serialize MongoDB ObjectId
def serialize_objectid(obj_id):
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    return obj_id

# Endpoint for user registration
@app.route("/auth/register", methods=["POST"])
def register():
    try:
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
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in user registration: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error"}), 500

# Endpoint for user login
@app.route("/auth/login", methods=["POST"])
def login():
    try:
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
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error"}), 500

# Replace print debugging with logger calls
@app.route("/analyze", methods=["POST"])
@jwt_required()  # Enable JWT requirement for authentication
def analyze():
    try:
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

    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")  # Use logger instead of print
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/history", methods=["GET"])
@jwt_required()  # Require authentication
def user_history():
    try:
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
        
    except Exception as e:
        logger.error(f"Error in user_history endpoint: {str(e)}")  # Replace print with logger
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/statistics", methods=["GET"])
@jwt_required()
def user_statistics():
    try:
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
        
    except Exception as e:
        logger.error(f"Error in user_statistics endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/history/<entry_id>", methods=["DELETE"])
@jwt_required()
def delete_history_entry(entry_id):
    try:
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
        
    except Exception as e:
        logger.error(f"Error in delete_history_entry endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/history", methods=["DELETE"])
@jwt_required()
def clear_history():
    try:
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
        
    except Exception as e:
        logger.error(f"Error in clear_history endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# Add a health check endpoint for Vercel
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
            db.command("ping")
            response["services"]["database"] = "Connected"
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
                        "last_reset_date": today
                    },
                    "$max": {"rewards": 5}  # Ensure rewards is at least 5
                }
            )
            
            # Get updated user data
            user = db.users.find_one({"_id": user["_id"]})
            
        return jsonify({
            "rewards": user.get("rewards", 0),
            "daily_count": user.get("daily_count", 0)
        }), 200
    except Exception as e:
        logger.error(f"Error in get_rewards endpoint: {str(e)}")
        return jsonify({"error": "Failed to get user rewards"}), 500

@app.route("/user/rewards", methods=["PUT"])
@jwt_required()
def update_rewards():
    try:
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
            
    except Exception as e:
        logger.error(f"Error in update_rewards endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/daily-count", methods=["POST"])
@jwt_required()
def increment_daily_count():
    try:
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
    except Exception as e:
        logger.error(f"Error in increment_daily_count endpoint: {str(e)}")
        return jsonify({"error": "Failed to increment daily count"}), 500

# Weekly mood endpoints
@app.route("/user/weekly-mood", methods=["POST"])
@jwt_required()
def add_weekly_mood():
    try:
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
            "date": datetime.now() if "date" not in data else datetime.fromisoformat(data["date"])
        }
        
        # Add to database
        result = db.weekly_moods.insert_one(new_weekly_mood)
        
        return jsonify({
            "message": "Weekly mood data saved successfully",
            "id": str(result.inserted_id)
        }), 200
            
    except Exception as e:
        logger.error(f"Error in add_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/weekly-mood", methods=["GET"])
@jwt_required()
def get_weekly_mood():
    try:
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
        for entry in weekly_entries:
            weekly_data.append({
                "id": str(entry["_id"]),
                "mood": entry["mood"],
                "date": entry["date"].isoformat() if isinstance(entry["date"], datetime) else entry["date"]
            })
        
        return jsonify({"weekly_data": weekly_data}), 200
        
    except Exception as e:
        logger.error(f"Error in get_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True)
