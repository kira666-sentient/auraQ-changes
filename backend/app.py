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
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import SQLAlchemy models
from models import db, User, MoodEntry, WeeklyMood

# Set up logging
log_dir = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
logger = logging.getLogger("aura_q")
logger.setLevel(logging.INFO)

# Create handlers
log_file = os.path.join(log_dir, "aura_q.log")
file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')  # 5MB per file, keep 5 backups
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatters
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Initialize app
app = Flask(__name__)
logger.info("Starting AuraQ backend application")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///aura_detector.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

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

# Create database tables at startup
with app.app_context():
    db.create_all()  # This replaces the deprecated @app.before_first_request decorator
    logger.info("Database tables created or verified")

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
        if User.query.filter_by(username=data["username"]).first():
            logger.info(f"Registration failed: username {data['username']} already exists")
            raise ApiError("Username already exists", 409)
        
        if User.query.filter_by(email=data["email"]).first():
            logger.info(f"Registration failed: email {data['email']} already exists")
            raise ApiError("Email already exists", 409)
        
        # Create new user
        new_user = User(
            username=data["username"],
            email=data["email"],
            password=data["password"]
        )
        
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"User {data['username']} registered successfully")
        
        # Generate access token
        access_token = create_access_token(identity=new_user.username)
        
        return jsonify({
            "message": "User registered successfully",
            "token": access_token,
            "username": new_user.username
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
        user = User.query.filter_by(username=data["username"]).first()
        
        # Verify user and password
        if not user or not user.check_password(data["password"]):
            logger.warning(f"Failed login attempt for username: {data.get('username', 'unknown')}")
            # Use same error message to prevent username enumeration
            raise ApiError("Invalid username or password", 401)
        
        # Update user's last login timestamp
        user.last_login = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        db.session.commit()
        
        logger.info(f"Successful login for user: {user.username}")
        
        # Generate access token
        access_token = create_access_token(identity=user.username)
        
        return jsonify({
            "message": "Login successful",
            "token": access_token,
            "username": user.username
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
        user = User.query.filter_by(username=username).first()
        
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
        new_entry = MoodEntry(
            user_id=user.id,
            mood=mood_feedback["mood"]
        )
        
        # Add to database
        db.session.add(new_entry)
        db.session.commit()
        
        # Include the entry ID in the response
        mood_feedback["id"] = new_entry.id
        
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
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get query parameters
        limit = request.args.get("limit", default=None, type=int)
        sort = request.args.get("sort", default="desc", type=str)
        
        # Query mood entries
        query = MoodEntry.query.filter_by(user_id=user.id)
        
        # Apply sorting
        if sort.lower() == "asc":
            query = query.order_by(MoodEntry.timestamp.asc())
        else:
            query = query.order_by(MoodEntry.timestamp.desc())
        
        # Apply limit if specified
        if limit is not None and isinstance(limit, int) and limit > 0:
            query = query.limit(limit)
        
        # Get entries
        entries = query.all()
        
        # Convert to dict
        history = [entry.to_dict() for entry in entries]
        
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
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get all mood entries for this user
        entries = MoodEntry.query.filter_by(user_id=user.id).all()
        
        # Count occurrences of each mood
        mood_counts = {}
        for entry in entries:
            mood = entry.mood
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        # Get recent entries
        recent_entries = MoodEntry.query.filter_by(user_id=user.id).order_by(MoodEntry.timestamp.desc()).limit(5).all()
        recent_moods = [entry.mood for entry in recent_entries]
        
        return jsonify({
            "total_entries": len(entries),
            "mood_counts": mood_counts,
            "recent_moods": recent_moods
        })
        
    except Exception as e:
        logger.error(f"Error in user_statistics endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/history/<int:entry_id>", methods=["DELETE"])
@jwt_required()
def delete_history_entry(entry_id):
    try:
        # Get current user from JWT token
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Find the entry
        entry = MoodEntry.query.filter_by(id=entry_id, user_id=user.id).first()
        
        if not entry:
            return jsonify({"error": "Entry not found"}), 404
        
        # Delete the entry
        db.session.delete(entry)
        db.session.commit()
        
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
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete all entries for this user
        MoodEntry.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        return jsonify({"message": "History cleared successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in clear_history endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# Add a health check endpoint for Vercel
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# Add routes for user rewards
@app.route("/user/rewards", methods=["GET"])
@jwt_required()
def get_rewards():
    try:
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if reset is needed
        today = datetime.now().strftime("%Y-%m-%d")
        if user.last_reset_date != today:
            user.daily_count = 0
            user.last_reset_date = today
            
            # Ensure rewards is at least 5 on a new day
            if user.rewards < 5:
                user.rewards = 5
                
            db.session.commit()
        
        return jsonify({
            "rewards": user.rewards,
            "daily_count": user.daily_count
        }), 200
    except Exception as e:
        logger.error(f"Error in get_rewards endpoint: {str(e)}")
        return jsonify({"error": "Failed to get user rewards"}), 500

@app.route("/user/rewards", methods=["PUT"])
@jwt_required()
def update_rewards():
    try:
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
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
        user.rewards = new_rewards
        db.session.commit()
        
        return jsonify({
            "message": "Rewards updated successfully",
            "rewards": user.rewards
        }), 200
            
    except Exception as e:
        logger.error(f"Error in update_rewards endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/daily-count", methods=["POST"])
@jwt_required()
def increment_daily_count():
    try:
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if reset is needed
        today = datetime.now().strftime("%Y-%m-%d")
        if user.last_reset_date != today:
            user.daily_count = 1  # First entry of the day
            user.last_reset_date = today
        else:
            # Increment daily count
            user.daily_count += 1
        
        db.session.commit()
        
        return jsonify({
            "message": "Daily count incremented",
            "daily_count": user.daily_count
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
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        
        if not data or "mood" not in data:
            return jsonify({"error": "No mood data provided"}), 400
        
        # Create new weekly mood entry
        new_weekly_mood = WeeklyMood(
            user_id=user.id,
            mood=data["mood"],
            date=datetime.now() if "date" not in data else datetime.fromisoformat(data["date"])
        )
        
        # Add to database
        db.session.add(new_weekly_mood)
        db.session.commit()
        
        return jsonify({"message": "Weekly mood data saved successfully"}), 200
            
    except Exception as e:
        logger.error(f"Error in add_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/user/weekly-mood", methods=["GET"])
@jwt_required()
def get_weekly_mood():
    try:
        username = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get entries from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        weekly_entries = WeeklyMood.query.filter(
            WeeklyMood.user_id == user.id,
            WeeklyMood.date >= thirty_days_ago
        ).order_by(WeeklyMood.date.desc()).all()
        
        # Convert to dict
        weekly_data = [entry.to_dict() for entry in weekly_entries]
        
        return jsonify({"weekly_data": weekly_data}), 200
        
    except Exception as e:
        logger.error(f"Error in get_weekly_mood endpoint: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True)
