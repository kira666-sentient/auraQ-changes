from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import secrets

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and metadata"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User metadata
    rewards = db.Column(db.Integer, default=5)
    daily_count = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.String(10), default=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    # Additional tracking fields
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # API key for potential future use
    api_key = db.Column(db.String(64), unique=True, default=lambda: secrets.token_hex(32))
    
    # Relationships
    mood_entries = db.relationship('MoodEntry', backref='user', lazy=True, cascade="all, delete-orphan")
    weekly_moods = db.relationship('WeeklyMood', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rewards': self.rewards,
            'daily_count': self.daily_count,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count
        }


class MoodEntry(db.Model):
    """Model for storing mood analysis entries"""
    __tablename__ = 'mood_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Note: We don't store the story text or feedback anymore
    
    def to_dict(self):
        return {
            'id': self.id,
            'mood': self.mood,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class WeeklyMood(db.Model):
    """Model for storing weekly mood review data"""
    __tablename__ = 'weekly_moods'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mood': self.mood,
            'date': self.date.isoformat() if self.date else None
        }