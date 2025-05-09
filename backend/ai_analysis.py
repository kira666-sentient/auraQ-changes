import os
import json
import re
import random
import logging
import sys
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv(override=True)

# Configure console-only logging
logger = logging.getLogger("aura_q")
logger.setLevel(logging.INFO)

# Only add handler if one doesn't exist already (prevent duplicates)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Enhanced error logging for Vercel
print("Initializing AI Analysis module")

# Try to import Gemini API with better error handling
GEMINI_AVAILABLE = False
try:
    print("Attempting to import Google Generative AI")
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("✅ Gemini API successfully imported")
except ImportError as e:
    print(f"❌ google.generativeai import error: {str(e)}")
    logger.warning(f"google.generativeai module not available: {str(e)}")
except Exception as e:
    print(f"❌ Unexpected error importing Gemini: {str(e)}")
    logger.error(f"Unexpected error importing Gemini: {str(e)}")
    logger.error(traceback.format_exc())

# Try to import TextBlob with better error handling
TEXTBLOB_AVAILABLE = False
try:
    print("Attempting to import TextBlob")
    from textblob import TextBlob
    
    # Handle NLTK data requirements for Vercel
    if "VERCEL" in os.environ:
        print("Running in Vercel environment - configuring NLTK data")
        import nltk
        
        # Set NLTK data path to /tmp which is writable in Vercel
        nltk_data_dir = "/tmp/nltk_data"
        os.environ["NLTK_DATA"] = nltk_data_dir
        
        # Create directory if it doesn't exist
        if not os.path.exists(nltk_data_dir):
            print(f"Creating NLTK data directory at {nltk_data_dir}")
            os.makedirs(nltk_data_dir, exist_ok=True)
            
        # Check if needed data exists, if not, download minimal required sets
        try:
            # Minimal data required by TextBlob
            for item in ['punkt', 'averaged_perceptron_tagger']:
                data_path = os.path.join(nltk_data_dir, item)
                if not os.path.exists(data_path):
                    print(f"Downloading NLTK data: {item}")
                    nltk.download(item, download_dir=nltk_data_dir, quiet=True)
                    print(f"Downloaded {item} to {nltk_data_dir}")
                else:
                    print(f"NLTK data {item} already exists")
        except Exception as e:
            print(f"Error downloading NLTK data: {str(e)}")
    
    # Test TextBlob minimally to ensure it's working
    test_blob = TextBlob("Test sentence")
    _ = test_blob.sentiment  # This will trigger NLTK data loading/errors if any
    
    TEXTBLOB_AVAILABLE = True
    print("✅ TextBlob successfully imported and tested")
except ImportError as e:
    print(f"❌ TextBlob import error: {str(e)}")
    logger.warning(f"TextBlob module not available: {str(e)}")
except Exception as e:
    print(f"❌ TextBlob initialization error: {str(e)}")
    logger.error(f"TextBlob initialization error: {str(e)}")
    logger.error(traceback.format_exc())

# Configure Gemini API if available
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        print(f"Configuring Gemini API with key (first 3 chars: {GEMINI_API_KEY[:3]}...)")
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API configured successfully")
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {str(e)}")
        logger.error(f"Failed to configure Gemini API: {str(e)}")
        logger.error(traceback.format_exc())
elif GEMINI_AVAILABLE:
    print("⚠️ Gemini API key not found in environment variables")
    logger.warning("Gemini API key not found in environment variables")

# Add simple non-AI backup for complete resilience
def generate_simple_analysis(story):
    """
    Extremely simple mood analysis as last resort backup
    """
    print("Using simple keyword-based analysis (last resort)")
    
    # Simple keyword matching
    positive_words = ['happy', 'good', 'great', 'excellent', 'joy', 'wonderful', 'love', 'like', 'amazing']
    negative_words = ['sad', 'bad', 'terrible', 'awful', 'hate', 'dislike', 'angry', 'upset', 'disappointed']
    
    # Convert to lowercase for case-insensitive matching
    story_lower = story.lower()
    
    # Count positive and negative words
    positive_count = sum(word in story_lower for word in positive_words)
    negative_count = sum(word in story_lower for word in negative_words)
    
    if positive_count > negative_count:
        mood = "joy"
    elif negative_count > positive_count:
        mood = "sadness"
    else:
        mood = "neutral"
    
    # Use a template response
    feedback = random.choice(FEEDBACK_TEMPLATES[mood])
    
    return {
        "mood": mood,
        "feedback": feedback,
        "model_used": "simple-keyword"
    }

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

def analyze_mood(story):
    """Analyze mood using available tools: Gemini API, TextBlob, or simple keyword analysis"""
    
    if not story:
        logger.warning("Empty story received")
        return {"mood": "neutral", "feedback": "No story provided."}

    # Try Gemini first if available
    if GEMINI_AVAILABLE and GEMINI_API_KEY:
        try:
            logger.info("Attempting Gemini analysis")
            result = analyze_with_gemini(story)
            if result:
                logger.info("Successfully analyzed with Gemini")
                return result
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            logger.error(traceback.format_exc())
    
    # If Gemini fails, try TextBlob
    if TEXTBLOB_AVAILABLE:
        try:
            logger.info("Using TextBlob fallback")
            result = analyze_with_textblob(story)
            logger.info("Successfully analyzed with TextBlob")
            return result
        except Exception as e:
            logger.error(f"TextBlob analysis failed: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Last resort: use simple keyword analysis
    logger.warning("Using simple analysis as last resort")
    return generate_simple_analysis(story)

def analyze_with_gemini(story):
    """Analyze mood using Google Gemini API"""
    if not GEMINI_API_KEY:
        return None
        
    try:
        model = genai.GenerativeModel("gemini-pro")
        
        prompt = f"""
        Analyze this text: "{story}"
        
        First, determine the primary emotion/mood (choose only ONE from: joy, sadness, anger, fear, surprise, disgust, neutral).
        
        Then create a personalized, compassionate response (1-2 sentences) directly addressing what the person wrote.
        Make your feedback empathetic, varied, and naturally conversational - like a supportive friend would respond.
        
        Return ONLY a valid JSON object with exactly this structure:
        {{"mood": "chosen_mood", "feedback": "your personalized response"}}
        
        IMPORTANT: Return raw JSON with no markdown formatting, code blocks, or additional text.
        """
        
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
        
        raw_response = response.text.strip()
        
        # Process response
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            cleaned_json = clean_json_response(raw_response)
            result = json.loads(cleaned_json)
        
        # Validate result
        if 'mood' not in result or 'feedback' not in result:
            return None
        
        # Normalize mood
        valid_moods = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]
        if result['mood'].lower() not in valid_moods:
            result['mood'] = get_closest_mood(result['mood'], valid_moods)
        
        result['model_used'] = "gemini"
        return result
    
    except Exception as e:
        logger.error(f"Gemini analysis error: {str(e)}")
        return None

def analyze_with_textblob(story):
    """Simple mood analysis using TextBlob sentiment"""
    if not TEXTBLOB_AVAILABLE:
        return {"mood": "neutral", "feedback": random.choice(FEEDBACK_TEMPLATES["neutral"])}
    
    blob = TextBlob(story)
    sentiment = blob.sentiment.polarity
    
    # Determine mood from sentiment
    if sentiment > 0.3:
        mood = "joy"
    elif sentiment < -0.3:
        mood = "sadness"
    else:
        mood = "neutral"
    
    # Generate feedback
    feedback = random.choice(FEEDBACK_TEMPLATES[mood])
    
    return {
        "mood": mood,
        "feedback": feedback,
        "model_used": "textblob"
    }

def clean_json_response(text):
    """Clean and extract JSON from the response text."""
    # Remove code block markers
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].strip()
    
    # Find JSON object pattern
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        text = json_match.group(0)
    
    # Fix common issues
    text = text.replace("'", '"')
    text = text.replace('\\n', ' ')
    text = text.replace('\\"', '"')
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
        "happy": "joy", "joyful": "joy", "excited": "joy", 
        "sad": "sadness", "unhappy": "sadness", "depressed": "sadness",
        "angry": "anger", "mad": "anger", "furious": "anger",
        "scared": "fear", "afraid": "fear", "anxious": "fear",
        "surprised": "surprise", "shocked": "surprise",
        "disgusted": "disgust", "repulsed": "disgust",
        "calm": "neutral", "ok": "neutral", "fine": "neutral"
    }
    
    for synonym, valid in mood_map.items():
        if synonym in invalid_mood:
            return valid
    
    # Default
    return "neutral"
