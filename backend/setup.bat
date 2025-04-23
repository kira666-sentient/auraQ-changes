@echo off
echo ==================================
echo AuraQ Backend Setup Script
echo ==================================
echo.

:: Check if .env file exists, if not create it
if not exist .env (
    echo Creating .env file with default values...
    echo # AuraQ Backend Environment Variables > .env
    echo JWT_SECRET_KEY=4290157aa6fa6b40a3660dcb2d7998de52a82e3f485cf6f11985ccb56ccb2736 >> .env
    echo GEMINI_API_KEY=your_gemini_api_key_here >> .env
    echo FLASK_APP=app.py >> .env
    echo FLASK_ENV=development >> .env
    echo. >> .env
    echo Created .env file. Please update the GEMINI_API_KEY value if needed.
    echo.
)

:: Check if virtual environment exists, if not create it
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo Failed to create virtual environment!
        goto :error
    )
    echo Virtual environment created successfully.
    echo.
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment!
    goto :error
)
echo.

:: Update pip to latest version
echo Updating pip to the latest version...
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo Warning: Failed to update pip, continuing with installed version...
)
echo.

:: Install dependencies with better error handling
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Dependency installation failed!
    echo.
    echo Trying alternative installation method...
    pip install --no-cache-dir -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Failed to install dependencies even with no-cache option.
        goto :error
    )
)
echo Dependencies installed successfully.
echo.

:: Download NLTK data
echo Downloading required NLTK data...
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
if %ERRORLEVEL% neq 0 (
    echo Warning: Failed to download NLTK data. Some features may not work correctly.
) else (
    echo NLTK data downloaded successfully.
)
echo.

:: Create database tables if they don't exist
echo Creating database tables...
python -c "from app import app, db; app.app_context().push(); db.create_all()"
if %ERRORLEVEL% neq 0 (
    echo Warning: Failed to create database tables!
) else (
    echo Database tables created successfully.
)
echo.

:: Success message
echo ==================================
echo Setup completed successfully!
echo.
echo To run the application, use:
echo python run.py
echo ==================================

:: Deactivate the virtual environment
call venv\Scripts\deactivate
goto :end

:error
echo.
echo ==================================
echo Setup failed! Please check the errors above.
echo ==================================
exit /b 1

:end
exit /b 0