import os
import json
from datetime import datetime

# Path to user data database file
USER_DATA_PATH = os.path.join(os.path.dirname(__file__), 'user_analysis.json')
# Maximum number of history entries to keep per user
MAX_HISTORY_ENTRIES = 100

def load_user_data():
    """Load user analysis data from JSON file"""
    if not os.path.exists(USER_DATA_PATH):
        return {}
    try:
        with open(USER_DATA_PATH, 'r') as file:
            return json.load(file)
    except:
        return {}

def save_user_data(user_data):
    """Save user analysis data to JSON file"""
    os.makedirs(os.path.dirname(USER_DATA_PATH), exist_ok=True)
    with open(USER_DATA_PATH, 'w') as file:
        json.dump(user_data, file, indent=2)

def add_user_analysis(username, story, analysis_result):
    """
    Add a new analysis entry for a user
    
    Parameters:
    - username: The user's username
    - story: The text submitted for analysis (not stored)
    - analysis_result: The result of the mood analysis
    """
    user_data = load_user_data()
    
    # Initialize the user's data if it doesn't exist
    if username not in user_data:
        user_data[username] = []
    
    # Create an entry with timestamp - NO STORY TEXT STORED
    entry = {
        "id": generate_entry_id(username),
        "timestamp": datetime.now().isoformat(),
        "mood": analysis_result["mood"],
        # We don't store the story text or detailed feedback anymore
    }
    
    # Add the entry to the user's data
    user_data[username].append(entry)
    
    # Limit the number of entries to MAX_HISTORY_ENTRIES
    if len(user_data[username]) > MAX_HISTORY_ENTRIES:
        user_data[username] = user_data[username][-MAX_HISTORY_ENTRIES:]
    
    # Save the updated data
    save_user_data(user_data)
    
    # Return the full analysis result to the client (but we've only stored minimal data)
    return {"id": entry["id"], **analysis_result}

def generate_entry_id(username):
    """Generate a unique ID for an entry"""
    user_data = load_user_data()
    entries = user_data.get(username, [])
    if not entries:
        return f"{username}_1"
    
    # Get the highest ID number and increment it
    last_id = max([int(entry.get('id', '').split('_')[-1]) if entry.get('id', '').split('_')[-1].isdigit() else 0 
                  for entry in entries] or [0])
    return f"{username}_{last_id + 1}"

def get_user_analysis_history(username, limit=None, sort='desc'):
    """
    Get the analysis history for a specific user
    
    Parameters:
    - username: The user's username
    - limit: Maximum number of entries to return (None for all)
    - sort: Sort order ('asc' or 'desc' by timestamp)
    
    Returns:
    - A list of analysis entries for the user
    """
    user_data = load_user_data()
    history = user_data.get(username, [])
    
    # Sort by timestamp
    if sort.lower() == 'asc':
        history = sorted(history, key=lambda x: x.get('timestamp', ''))
    else:
        history = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Apply limit if specified
    if limit is not None and isinstance(limit, int) and limit > 0:
        history = history[:limit]
        
    return history

def delete_user_entry(username, entry_id):
    """
    Delete a specific entry from a user's history
    
    Parameters:
    - username: The user's username
    - entry_id: The ID of the entry to delete
    
    Returns:
    - True if deleted successfully, False otherwise
    """
    user_data = load_user_data()
    
    # Check if user exists
    if username not in user_data:
        return False
    
    # Find and remove the entry
    initial_length = len(user_data[username])
    user_data[username] = [entry for entry in user_data[username] if entry.get('id') != entry_id]
    
    # Check if an entry was removed
    if len(user_data[username]) < initial_length:
        save_user_data(user_data)
        return True
    
    return False

def clear_user_history(username):
    """
    Clear all history for a specific user
    
    Parameters:
    - username: The user's username
    
    Returns:
    - True if cleared successfully, False otherwise
    """
    user_data = load_user_data()
    
    # Check if user exists
    if username not in user_data:
        return False
    
    # Clear the user's data
    user_data[username] = []
    save_user_data(user_data)
    return True

def get_mood_statistics(username):
    """
    Get statistics about a user's mood history
    
    Parameters:
    - username: The user's username
    
    Returns:
    - A dictionary with mood statistics
    """
    history = get_user_analysis_history(username)
    
    if not history:
        return {"total_entries": 0, "mood_counts": {}, "recent_trend": None}
    
    # Count occurrences of each mood
    mood_counts = {}
    for entry in history:
        mood = entry.get('mood')
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
    
    # Calculate the most recent trend (last 5 entries)
    recent_entries = history[:5]
    recent_moods = [entry.get('mood') for entry in recent_entries if entry.get('mood')]
    
    return {
        "total_entries": len(history),
        "mood_counts": mood_counts,
        "recent_moods": recent_moods
    }

def get_user_rewards(username):
    """
    Get the current rewards for a specific user
    
    Parameters:
    - username: The user's username
    
    Returns:
    - The number of rewards/credits the user has, or 5 if not set
    """
    user_data = load_user_data()
    
    # If the user exists but has no rewards field, it will create the user entry
    if username not in user_data:
        user_data[username] = []
    
    # Check if user has a rewards field in their metadata
    if not isinstance(user_data.get(username + "_meta"), dict):
        user_data[username + "_meta"] = {"rewards": 5, "daily_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-%d")}
        save_user_data(user_data)
        return 5
    
    # If the user has no rewards field, create it with default value
    if "rewards" not in user_data[username + "_meta"]:
        user_data[username + "_meta"]["rewards"] = 5
        save_user_data(user_data)
        return 5
        
    return user_data[username + "_meta"]["rewards"]

def update_user_rewards(username, new_rewards):
    """
    Update the rewards for a specific user
    
    Parameters:
    - username: The user's username
    - new_rewards: The new number of rewards
    
    Returns:
    - True if updated successfully, False otherwise
    """
    user_data = load_user_data()
    
    # Initialize user metadata if it doesn't exist
    if username + "_meta" not in user_data:
        user_data[username + "_meta"] = {}
    
    # Update the rewards
    user_data[username + "_meta"]["rewards"] = new_rewards
    save_user_data(user_data)
    return True

def get_user_daily_count(username):
    """
    Get the daily story count for a specific user
    
    Parameters:
    - username: The user's username
    
    Returns:
    - The number of stories submitted today, or 0 if not set
    """
    user_data = load_user_data()
    
    # Check if user has metadata
    if username + "_meta" not in user_data:
        user_data[username + "_meta"] = {"rewards": 5, "daily_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-%d")}
        save_user_data(user_data)
        return 0
    
    # Check if the date needs to be reset
    today = datetime.now().strftime("%Y-%m-%d")
    if "last_reset_date" not in user_data[username + "_meta"] or user_data[username + "_meta"]["last_reset_date"] != today:
        user_data[username + "_meta"]["daily_count"] = 0
        user_data[username + "_meta"]["last_reset_date"] = today
        
        # Ensure rewards is at least 5 on a new day
        if "rewards" not in user_data[username + "_meta"] or user_data[username + "_meta"]["rewards"] < 5:
            user_data[username + "_meta"]["rewards"] = 5
            
        save_user_data(user_data)
        return 0
        
    return user_data[username + "_meta"].get("daily_count", 0)

def increment_user_daily_count(username):
    """
    Increment the daily story count for a specific user
    
    Parameters:
    - username: The user's username
    
    Returns:
    - The new daily count
    """
    user_data = load_user_data()
    
    # Initialize metadata if needed
    if username + "_meta" not in user_data:
        user_data[username + "_meta"] = {"rewards": 5, "daily_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-%d")}
    
    # Check if the date needs to be reset
    today = datetime.now().strftime("%Y-%m-%d")
    if "last_reset_date" not in user_data[username + "_meta"] or user_data[username + "_meta"]["last_reset_date"] != today:
        user_data[username + "_meta"]["daily_count"] = 1
        user_data[username + "_meta"]["last_reset_date"] = today
    else:
        # Increment the daily count
        user_data[username + "_meta"]["daily_count"] = user_data[username + "_meta"].get("daily_count", 0) + 1
    
    save_user_data(user_data)
    return user_data[username + "_meta"]["daily_count"]

def save_weekly_mood(username, mood_data):
    """
    Save a new mood entry for the weekly review
    
    Parameters:
    - username: The user's username
    - mood_data: Dict containing mood and timestamp
    
    Returns:
    - True if saved successfully
    """
    user_data = load_user_data()
    
    # Initialize user weekly data if it doesn't exist
    if username + "_weekly" not in user_data:
        user_data[username + "_weekly"] = []
    
    # Add timestamp if not provided
    if "date" not in mood_data:
        mood_data["date"] = datetime.now().isoformat()
    
    # Add the mood data to the weekly array
    user_data[username + "_weekly"].append(mood_data)
    
    # Keep only the most recent entries (last 30 days)
    thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
    user_data[username + "_weekly"] = [
        entry for entry in user_data[username + "_weekly"]
        if datetime.fromisoformat(entry.get("date", datetime.now().isoformat())).timestamp() > thirty_days_ago
    ]
    
    # Save the updated data
    save_user_data(user_data)
    return True

def get_weekly_mood_data(username):
    """
    Get the weekly mood data for a specific user
    
    Parameters:
    - username: The user's username
    
    Returns:
    - A list of weekly mood entries
    """
    user_data = load_user_data()
    
    # Return empty list if no weekly data exists
    if username + "_weekly" not in user_data:
        return []
    
    # Sort by date (newest first)
    weekly_data = sorted(
        user_data[username + "_weekly"],
        key=lambda x: x.get("date", ""),
        reverse=True
    )
    
    return weekly_data