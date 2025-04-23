import os
import json
import re
import random
import time
import logging
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging for model performance tracking
log_dir = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

model_logger = logging.getLogger("model_performance")
model_logger.setLevel(logging.INFO)

# Create handlers
perf_log_file = os.path.join(log_dir, "model_performance.log")
file_handler = logging.FileHandler(perf_log_file)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
model_logger.addHandler(file_handler)

# Make imports resilient to failures
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    model_logger.info("Gemini API successfully imported")
except ImportError:
    model_logger.warning("google.generativeai module not available")
    GEMINI_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
    model_logger.info("TextBlob successfully imported")
except ImportError:
    model_logger.warning("TextBlob module not available")
    TEXTBLOB_AVAILABLE = False

# Try to import scikit-learn dependencies
try:
    import numpy as np
    import joblib
    SKLEARN_REQUIREMENTS_MET = True
    
    # Only try to import sklearn if its requirements are met
    try:
        import sklearn
        SKLEARN_AVAILABLE = True
        model_logger.info("scikit-learn successfully imported")
    except ImportError:
        model_logger.warning("scikit-learn module not available, falling back to alternatives")
        SKLEARN_AVAILABLE = False
except ImportError:
    model_logger.warning("numpy or joblib not available, falling back to alternatives")
    SKLEARN_REQUIREMENTS_MET = False
    SKLEARN_AVAILABLE = False

# Performance tracking decorator
def track_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        model_name = func.__name__
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Add which model was used to the result
            if result and isinstance(result, dict):
                result["model_used"] = model_name.replace("analyze_with_", "")
            
            # Log performance data
            text_length = len(args[0]) if args else 0
            model_logger.info(f"Model: {model_name} | Duration: {duration:.2f}s | Length: {text_length} | Success: True")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            model_logger.error(f"Model: {model_name} | Duration: {duration:.2f}s | Error: {str(e)}")
            raise
    
    return wrapper

# Initialize the Gemini API with your key if available
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_logger.info("Gemini API configured with key")
        print(f"Gemini API configured with key: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    except Exception as e:
        model_logger.error(f"Failed to configure Gemini API: {str(e)}")
        print(f"Error configuring Gemini API: {str(e)}")
elif GEMINI_AVAILABLE:
    model_logger.warning("No Gemini API key found in environment")
    print("Warning: No Gemini API key found in environment variables")
else:
    print("google.generativeai module not available - you may need to install it with: pip install google-generativeai")

# Path to model and vectorizer files
MODEL_PATH = Path(os.path.dirname(__file__)) / "emotion_model.pkl"
VECTORIZER_PATH = Path(os.path.dirname(__file__)) / "vectorizer.pkl"

# Pre-load models if they exist and sklearn is available
naive_bayes_model = None
vectorizer = None

if SKLEARN_REQUIREMENTS_MET and SKLEARN_AVAILABLE:
    try:
        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            model_logger.info("Attempting to load pretrained models")
            naive_bayes_model = joblib.load(MODEL_PATH)
            vectorizer = joblib.load(VECTORIZER_PATH)
            model_logger.info("Successfully loaded Naive Bayes model and vectorizer")
    except Exception as e:
        model_logger.error(f"Failed to load Naive Bayes model: {str(e)}")

# Define feedback templates for each mood
FEEDBACK_TEMPLATES = {
    "joy": [
        "It's wonderful to see you're feeling positive! Your joy comes through clearly in your words.",
        "Your upbeat mood is inspiring! It's great to see you in such good spirits."
    ],
    
    "sadness": [
        "I notice you might be feeling down. Remember that difficult times do pass, and you're not alone in this.",
        "I sense some sadness in your words. It's okay to feel this way, and sharing your feelings is a positive step."
    ],
    
    "anger": [
        "I can sense your frustration. Taking deep breaths might help clear your mind and process these intense feelings.",
        "It sounds like you're feeling upset about this situation. Your feelings are valid, and it's okay to acknowledge them."
    ],
    
    "fear": [
        "It seems you might be feeling anxious. Remember, you're stronger than you think, and many fears we face never materialize.",
        "I understand that feeling uncertain can be scary. You're not alone in experiencing these worries."
    ],
    
    "surprise": [
        "What an unexpected turn of events! How are you processing this surprise?",
        "Life can certainly be surprising sometimes! This seems like something that caught you off guard."
    ],
    
    "disgust": [
        "I understand this situation might be unpleasant for you. It's natural to have strong reactions to things we find objectionable.",
        "Some experiences can be quite off-putting. Your reaction seems completely understandable."
    ],
    
    "neutral": [
        "Thank you for sharing your thoughts. I appreciate your balanced perspective.",
        "I appreciate you taking the time to write this. Your measured approach comes through in your words."
    ]
}

@track_performance
def analyze_mood(story):
    """Analyze mood using Google Gemini API with Naive Bayes fallback."""
    
    if not story:
        model_logger.warning("Empty story received")
        return {"mood": "Unknown", "feedback": "No story provided."}

    # Try Gemini first if available
    if GEMINI_AVAILABLE and GEMINI_API_KEY:
        try:
            model_logger.info("Attempting Gemini analysis")
            result = analyze_with_gemini(story)
            if result:
                return result
        except Exception as e:
            model_logger.error(f"Gemini API error: {str(e)}")
    
    # Try Naive Bayes next if available
    if SKLEARN_REQUIREMENTS_MET and SKLEARN_AVAILABLE and naive_bayes_model is not None:
        try:
            model_logger.info("Attempting Naive Bayes analysis")
            result = naive_bayes_fallback(story)
            if result:
                return result
        except Exception as e:
            model_logger.error(f"Naive Bayes fallback failed: {str(e)}")
    
    # Last resort: simple fallback
    try:
        model_logger.info("Attempting basic sentiment analysis")
        return simple_fallback(story)
    except Exception as e:
        model_logger.error(f"All mood analysis methods failed: {str(e)}")
        return {"mood": "neutral", "feedback": "Thank you for sharing your thoughts with me."}

@track_performance
def analyze_with_gemini(story):
    """Analyze mood using Google Gemini API."""
    
    # Check if API key is configured
    if not GEMINI_API_KEY:
        print("ERROR: No Gemini API key available")
        return None
        
    try:
        # Try to get available models with better error handling
        try:
            print("Attempting to list available Gemini models...")
            available_models = [m.name for m in genai.list_models()]
            print(f"Available Gemini models: {available_models}")
        except Exception as e:
            print(f"Error listing Gemini models: {str(e)}")
            # Try a direct approach with a known model instead of listing
            print("Falling back to direct model usage...")
            available_models = []
    
        # Filter for modern models - prioritizing the stable ones
        preferred_models = [
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro", 
            "models/gemini-pro",  # Added classic model name
            "gemini-pro",         # Added alternative format
            "models/gemini-1.0-pro",
            "models/gemini-1.5-flash-latest"
        ]
        
        # Try to use one of the preferred models
        model_name = None
        for preferred in preferred_models:
            if preferred in available_models or not available_models:  # Continue if we couldn't list models
                model_name = preferred
                break
        
        if not model_name:
            # If no suitable model found
            print("No suitable Gemini model found, using default gemini-pro")
            model_name = "gemini-pro"  # Use default model
        
        print(f"Using Gemini model: {model_name}")
        
        # Configure the model with error catching
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"Error configuring model {model_name}: {str(e)}")
            return None
        
        # Prompt focusing on direct mood classification and feedback generation
        prompt = f"""
        Analyze this text: "{story}"
        
        First, determine the primary emotion/mood (choose only ONE from: joy, sadness, anger, fear, surprise, disgust, neutral).
        
        Then create a personalized, compassionate response (1-2 sentences) directly addressing what the person wrote.
        Make your feedback empathetic, varied, and naturally conversational - like a supportive friend would respond.
        
        Return ONLY a valid JSON object with exactly this structure:
        {{"mood": "chosen_mood", "feedback": "your personalized response"}}
        
        IMPORTANT: Return raw JSON with no markdown formatting, code blocks, or additional text.
        """
        
        # Generate response from Gemini with specific configuration and error handling
        try:
            print("Sending request to Gemini API...")
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 200,
                    "response_mime_type": "application/json"
                }
            )
            print("Successfully received response from Gemini API")
            
            # Get the raw response and log it
            raw_response = response.text.strip()
            print(f"Raw Gemini response: {raw_response}")
            
        except Exception as e:
            print(f"Error generating content from Gemini: {str(e)}")
            return None
        
        # Extract JSON - improved handling
        try:
            # First attempt: Try direct parsing (if the response is already clean JSON)
            try:
                result = json.loads(raw_response)
                print("Successfully parsed JSON directly")
            except json.JSONDecodeError:
                # Clean the response and try again
                cleaned_json = clean_json_response(raw_response)
                print(f"Cleaned JSON: {cleaned_json}")
                result = json.loads(cleaned_json)
            
            # Validate the result has the required fields
            if 'mood' not in result or 'feedback' not in result:
                print(f"WARNING: Missing expected fields in Gemini response: {result}")
                return None
            
            # Ensure mood is one of the valid moods
            valid_moods = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]
            if result['mood'].lower() not in valid_moods:
                closest_mood = get_closest_mood(result['mood'], valid_moods)
                result['mood'] = closest_mood
            
            print(f"AI analyzed mood: {result['mood']}, feedback: {result['feedback']}")
            return result
        except Exception as e:
            print(f"ERROR: Failed to process Gemini response: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Unexpected error in analyze_with_gemini: {str(e)}")
        return None

def naive_bayes_fallback(story):
    """Analyze mood using Naive Bayes classifier as a fallback."""
    if naive_bayes_model is None or vectorizer is None:
        print("Naive Bayes model or vectorizer not available")
        return None
        
    # Transform the input text using the vectorizer
    features = vectorizer.transform([story])
    
    # Predict the mood
    mood = naive_bayes_model.predict(features)[0]
    
    # Get probabilities to determine confidence
    probabilities = naive_bayes_model.predict_proba(features)[0]
    max_prob = max(probabilities)
    
    # Log the prediction details
    print(f"Naive Bayes predicted mood: {mood} with confidence: {max_prob:.2f}")
    
    # Generate appropriate feedback based on the mood
    mood_lower = mood.lower()
    if mood_lower in FEEDBACK_TEMPLATES:
        feedback = random.choice(FEEDBACK_TEMPLATES[mood_lower])
    else:
        # Map to closest mood
        closest_mood = get_closest_mood(mood_lower, list(FEEDBACK_TEMPLATES.keys()))
        feedback = random.choice(FEEDBACK_TEMPLATES[closest_mood])
        
    return {
        "mood": mood,
        "feedback": feedback
    }

def simple_fallback(story):
    """Absolute emergency fallback using basic sentiment."""
    if not TEXTBLOB_AVAILABLE:
        return {"mood": "neutral", "feedback": random.choice(FEEDBACK_TEMPLATES["neutral"])}
        
    blob = TextBlob(story)
    sentiment = blob.sentiment.polarity
    
    # Determine basic mood from sentiment
    if sentiment > 0.3:
        mood = "joy"
    elif sentiment < -0.3:
        mood = "sadness"
    else:
        mood = "neutral"
        
    # Generate a response using templates
    feedback = random.choice(FEEDBACK_TEMPLATES[mood])
    
    print(f"Basic sentiment analysis detected mood: {mood} (sentiment: {sentiment:.2f})")
    
    return {
        "mood": mood,
        "feedback": feedback
    }

def clean_json_response(text):
    """Clean and extract JSON from the response text."""
    # Remove code block markers
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].strip()
    
    # Use regex to find JSON object pattern
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        text = json_match.group(0)
    
    # Replace single quotes with double quotes
    text = text.replace("'", '"')
    
    # Fix escape sequences
    text = text.replace('\\n', ' ')
    text = text.replace('\\"', '"')
    
    # Fix any trailing commas before closing braces
    text = re.sub(r',\s*}', '}', text)
    
    return text

def get_closest_mood(invalid_mood, valid_moods):
    """Map an invalid mood to the closest valid one."""
    invalid_mood = invalid_mood.lower()
    
    # Direct match
    for valid in valid_moods:
        if valid == invalid_mood:
            return valid
    
    # Substring match
    for valid in valid_moods:
        if valid in invalid_mood:
            return valid
    
    # Common synonyms
    mood_map = {
        "happy": "joy", "joyful": "joy", "excited": "joy", "elated": "joy", "pleased": "joy",
        "sad": "sadness", "unhappy": "sadness", "depressed": "sadness", "gloomy": "sadness",
        "angry": "anger", "mad": "anger", "furious": "anger", "irritated": "anger",
        "scared": "fear", "afraid": "fear", "anxious": "fear", "worried": "fear",
        "surprised": "surprise", "shocked": "surprise", "astonished": "surprise",
        "disgusted": "disgust", "repulsed": "disgust", "revolted": "disgust",
        "calm": "neutral", "ok": "neutral", "fine": "neutral", "balanced": "neutral"
    }
    
    for synonym, valid in mood_map.items():
        if synonym in invalid_mood:
            return valid
    
    # If all else fails, default to neutral
    return "neutral"
