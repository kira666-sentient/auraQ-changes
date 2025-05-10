#!/usr/bin/env python
"""
Script to insert two test users into the MongoDB database.
Usage: 
  cd backend
  python add_test_users.py
Make sure MONGODB_URI (or db_username/db_password) is set in environment or .env.
"""
from datetime import datetime
import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from dotenv import load_dotenv

load_dotenv()

def main():
    # Initialize minimal Flask app for PyMongo and Bcrypt
    app = Flask(__name__)
    # Load the same config as app.py
    if os.environ.get("db_username") and os.environ.get("db_password"):
        uri = f"mongodb+srv://{os.environ['db_username']}:{os.environ['db_password']}@cluster0.g4j7ljt.mongodb.net/auraQ?retryWrites=true&w=majority"
    else:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/auraQ")
    app.config["MONGO_URI"] = uri
    mongo = PyMongo(app)
    db = mongo.db
    bcrypt = Bcrypt(app)

    # Define test users
    test_users = [
        {
            "username": "testuser3",
            "email": "test3@example.com",
            "password": bcrypt.generate_password_hash("Password123!").decode('utf-8'),
            "created_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "rewards": 5,
            "daily_count": 0,
            "last_reset_date": datetime.utcnow().strftime("%Y-%m-%d")
        },
        {
            "username": "testuser4",
            "email": "test4@example.com",
            "password": bcrypt.generate_password_hash("Secret456$").decode('utf-8'),
            "created_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "rewards": 5,
            "daily_count": 0,
            "last_reset_date": datetime.utcnow().strftime("%Y-%m-%d")
        }
    ]

    # Insert users
    result = db.users.insert_many(test_users)
    print(f"Inserted test users with IDs: {result.inserted_ids}")

if __name__ == '__main__':
    main()
