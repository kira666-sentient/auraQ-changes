# AuraQ - AI-Powered Mood Analysis Journal

AuraQ is an intelligent journaling platform that helps users track and understand their emotional patterns through AI-powered mood analysis. Users can submit journal entries, receive mood analysis and personalized feedback, and view their emotional trends over time.

## Features

- **AI-Powered Mood Analysis**: Uses Google Gemini AI with fallbacks to Naive Bayes and TextBlob
- **Secure User Authentication**: JWT-based login and registration system
- **Weekly Mood Review**: Visual dashboard of your emotional patterns
- **Daily Rewards System**: Gamification elements to encourage regular journaling
- **Responsive Design**: Works on desktop and mobile devices

## System Requirements

- Python 3.8 or higher (tested with Python 3.12)
- Node.js and npm (for development tools)
- SQLite (included)
- Google Gemini API key (optional, system will use fallbacks if not provided)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd auraQ-changes
```

### 2. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a Python virtual environment:
   ```bash
   # For Windows
   python -m venv venv
   venv\Scripts\activate

   # For macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. Create a `.env` file with the following content:
   ```
   JWT_SECRET_KEY=your_secure_random_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   FLASK_APP=app.py
   FLASK_ENV=development
   ```

4. Run the improved setup script:
   ```bash
   python run.py
   ```

   This will:
   - Install all dependencies from requirements.txt
   - Set up the database
   - Download required NLTK data
   - Start the Flask development server

   The backend will be available at http://127.0.0.1:5000

### 3. Frontend Setup

1. You can serve the frontend using any static file server. For local development, you can use:
   - Visual Studio Code's Live Server extension
   - Python's built-in HTTP server

2. Using Python's HTTP server:
   ```bash
   cd frontend
   python -m http.server 8080
   ```

   The frontend will be available at http://localhost:8080

3. Open your browser and navigate to:
   - http://localhost:8080/pages/signup.html to create an account
   - http://localhost:8080/pages/login.html to log in
   - http://localhost:8080/pages/dashboard.html to access the dashboard (requires authentication)

## Deploying to Vercel

### Backend Deployment

1. Make sure you have the Vercel CLI installed:
   ```bash
   npm install -g vercel
   ```

2. Navigate to the backend directory:
   ```bash
   cd backend
   ```

3. Login to Vercel:
   ```bash
   vercel login
   ```

4. Deploy to Vercel:
   ```bash
   vercel
   ```

5. When prompted:
   - Set the output directory to `backend`
   - Configure the project as needed
   - Set environment variables (JWT_SECRET_KEY and GEMINI_API_KEY)

6. For production deployment:
   ```bash
   vercel --prod
   ```

7. Note the deployment URL for configuring the frontend

### Frontend Deployment

1. Update API endpoints:
   Edit `frontend/js/main.js` and replace API URLs with your Vercel backend URL:
   
   ```javascript
   // Update this line in fetchWithAuth function and other fetch calls
   const API_BASE_URL = "https://your-vercel-backend-url.vercel.app";
   ```

2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

3. Deploy to Vercel:
   ```bash
   vercel
   ```

4. For production deployment:
   ```bash
   vercel --prod
   ```

## System Architecture

AuraQ is built with a clean separation between frontend and backend:

- **Frontend**: HTML, CSS, and vanilla JavaScript
- **Backend**: Flask API with SQLite database
- **ML Components**: Google Gemini API with Naive Bayes fallback

## Troubleshooting

### Backend Issues

1. **Dependencies not installing correctly**:
   - Make sure you're using Python 3.8 or higher
   - Try installing dependencies manually: `pip install -r requirements.txt`

2. **Database errors**:
   - Check if the `instance` directory exists in the backend folder
   - If issues persist, delete `instance/aura_detector.db` and restart

3. **API key issues**:
   - Ensure GEMINI_API_KEY is correctly set in your .env file
   - If unavailable, the system will fall back to local ML models

### Frontend Issues

1. **Authentication errors**:
   - Clear browser storage: localStorage and sessionStorage
   - Ensure backend is running and accessible

2. **CORS errors**:
   - Check that backend CORS settings include your frontend origin
   - For local development, ensure frontend runs on an allowed port (5500, 8080, etc.)

3. **Weekly mood review not showing**:
   - Submit at least one journal entry
   - Check browser console for API errors

## License

[Add your license information here]

## Contact

[Your contact information]