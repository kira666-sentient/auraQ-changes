"""
Migration script to transfer data from JSON files to SQL database
"""
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, MoodEntry, WeeklyMood

def migrate_users():
    """Migrate users from users.json to SQL database"""
    print("Migrating users...")
    user_file = os.path.join(os.path.dirname(__file__), 'users.json')
    
    if not os.path.exists(user_file):
        print("No users.json file found. Skipping user migration.")
        return
    
    try:
        with open(user_file, 'r') as file:
            users_data = json.load(file)
            
        # Iterate through users and add them to the database
        for username, user_info in users_data.items():
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                print(f"User {username} already exists in database. Skipping.")
                continue
                
            email = user_info.get('email', f"{username}@example.com")  # Default email if not present
            password_hash = user_info.get('password_hash')
            
            new_user = User(
                username=username,
                email=email,
                password="temporary_password"  # Will be replaced with hash below
            )
            
            # If we have an existing password hash, use it directly
            if password_hash:
                new_user.password_hash = password_hash
            
            db.session.add(new_user)
            print(f"Added user: {username}")
            
        db.session.commit()
        print(f"Successfully migrated {len(users_data)} users")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error migrating users: {str(e)}")

def migrate_user_data():
    """Migrate user analysis data from user_analysis.json to SQL database"""
    print("Migrating user analysis data...")
    data_file = os.path.join(os.path.dirname(__file__), 'user_analysis.json')
    
    if not os.path.exists(data_file):
        print("No user_analysis.json file found. Skipping data migration.")
        return
    
    try:
        with open(data_file, 'r') as file:
            user_data = json.load(file)
            
        # Iterate through users
        for username, data in user_data.items():
            # Skip metadata entries
            if username.endswith("_meta") or username.endswith("_weekly"):
                continue
                
            # Find user in database
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"User {username} not found in database. Skipping data.")
                continue
            
            # Migrate mood entries (only storing mood and timestamp, not story or feedback)
            count = 0
            for entry in data:
                if isinstance(entry, dict) and 'mood' in entry and 'timestamp' in entry:
                    try:
                        timestamp = datetime.fromisoformat(entry['timestamp'])
                    except:
                        timestamp = datetime.now()
                    
                    mood_entry = MoodEntry(
                        user_id=user.id,
                        mood=entry['mood'],
                        timestamp=timestamp
                    )
                    db.session.add(mood_entry)
                    count += 1
            
            print(f"Added {count} mood entries for {username}")
            
            # Migrate user metadata if it exists
            if username + "_meta" in user_data:
                meta = user_data[username + "_meta"]
                if 'rewards' in meta:
                    user.rewards = meta['rewards']
                if 'daily_count' in meta:
                    user.daily_count = meta['daily_count']
                if 'last_reset_date' in meta:
                    user.last_reset_date = meta['last_reset_date']
                print(f"Updated metadata for {username}")
                
            # Migrate weekly mood data if it exists
            if username + "_weekly" in user_data:
                weekly_data = user_data[username + "_weekly"]
                weekly_count = 0
                
                for entry in weekly_data:
                    if isinstance(entry, dict) and 'mood' in entry and 'date' in entry:
                        try:
                            entry_date = datetime.fromisoformat(entry['date'])
                        except:
                            entry_date = datetime.now()
                        
                        weekly_mood = WeeklyMood(
                            user_id=user.id,
                            mood=entry['mood'],
                            date=entry_date
                        )
                        db.session.add(weekly_mood)
                        weekly_count += 1
                
                print(f"Added {weekly_count} weekly mood entries for {username}")
            
        db.session.commit()
        print("User data migration completed successfully")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error migrating user data: {str(e)}")

def run_migration():
    """Run the full migration process"""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Run migrations
        migrate_users()
        migrate_user_data()
        
        print("Migration complete!")

if __name__ == "__main__":
    run_migration()