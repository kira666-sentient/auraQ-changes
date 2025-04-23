from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
import json
import os

# Create a Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Initialize bcrypt
bcrypt = Bcrypt()

# Path to users database file
USERS_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.json')


# Helper function to load users from JSON file
def load_users():
    if not os.path.exists(USERS_DB_PATH):
        return {}
    try:
        with open(USERS_DB_PATH, 'r') as file:
            return json.load(file)
    except:
        return {}

# Helper function to save users to JSON file
def save_users(users):
    os.makedirs(os.path.dirname(USERS_DB_PATH), exist_ok=True)
    with open(USERS_DB_PATH, 'w') as file:
        json.dump(users, file)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data['username']
    password = data['password']
    
    # Load existing users
    users = load_users()
    
    # Check if username already exists
    if username in users:
        return jsonify({"error": "Username already exists"}), 409
    
    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Add new user
    users[username] = hashed_password
    save_users(users)
    
    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data['username']
    password = data['password']
    
    # Load users
    users = load_users()
    
    # Check if user exists and password is correct
    if username not in users or not bcrypt.check_password_hash(users[username], password):
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Create access token
    access_token = create_access_token(identity=username)
    return jsonify({"token": access_token}), 200