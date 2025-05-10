// Global variables for credit system
let dailyStoryCount = 0;
let rewards = 5; // Default until we load from server
let maxDailyFreeSubmissions = 2; // Users get 2 free submissions per day
// Guard to prevent duplicate submissions
let isStoryProcessing = false;
// Variable to track if data has been loaded from server
let userDataLoaded = false;

document.addEventListener("DOMContentLoaded", function () {
    // Show the loading overlay initially
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('active');
    }

    // Check authentication status first before trying to access the dashboard
    const token = tokenManager.getToken();
    if (!token) {
        console.log("No authentication token found. User will be redirected to login page.");
        // Don't run any dashboard code to avoid errors
        return;
    }

    // Get all required UI elements
    const storyFormContainer = document.getElementById("story-form");
    const storyInput = document.getElementById("story-input");
    const submitButton = document.getElementById("submit-story");
    const moodDisplay = document.getElementById("mood-display");
    const feedbackDisplay = document.getElementById("feedback-display");
    const dateDisplay = document.getElementById("current-date");

    console.log("Dashboard loading: UI Elements found?", {
        storyFormContainer: !!storyFormContainer,
        storyInput: !!storyInput,
        submitButton: !!submitButton,
        moodDisplay: !!moodDisplay,
        feedbackDisplay: !!feedbackDisplay,
        dateDisplay: !!dateDisplay
    });

    // Skip if any required elements are missing
    if (!storyFormContainer || !storyInput || !submitButton) {
        console.error("Critical dashboard elements not found");
        return;
    }

    // Load user data from server (rewards and daily count) 
    // and use async/await with proper error handling
    (async function() {
        try {
            console.log("Initial state before fetch - dailyStoryCount:", dailyStoryCount, 
                      "maxDailyFreeSubmissions:", maxDailyFreeSubmissions,
                      "rewards:", rewards);
                      
            await fetchUserRewards();
            console.log("User data loaded successfully");
            console.log("After fetch - dailyStoryCount:", dailyStoryCount, 
                      "maxDailyFreeSubmissions:", maxDailyFreeSubmissions,
                      "rewards:", rewards);
            
            // Update UI to reflect credit status immediately
            if (dailyStoryCount >= maxDailyFreeSubmissions && rewards <= 0) {
                console.log("User has no credits and used all free entries - disabling submit button");
                submitButton.disabled = true;
                submitButton.title = "No credits remaining";
                submitButton.classList.add("disabled");
            } else {
                console.log("User still has either free entries or credits left");
            }
        } catch (error) {
            console.error("Error during initial data load:", error);
            // Still allow application to function with defaults
            userDataLoaded = true; // Set to true even on error so UI isn't blocked
            updateUIBasedOnUserData(); // MODIFIED: Call updateUIBasedOnUserData even on error to reflect default/current state
        }
    })();
    
    // Restore any saved results from localStorage (to handle refresh)
    restoreResultsFromStorage();

    // Safely set username if the element exists
    const storedUsername = tokenManager.getUsername();
    const usernameElement = document.getElementById("username");
    if (usernameElement) {
        console.log("Setting username display. Element found:", !!usernameElement, "Username string:", storedUsername);
        usernameElement.textContent = storedUsername;
    } else {
        console.error("Username display element (#username) not found!");
    }

    // Safely set date if the element exists - Fixed date formatting to show correct day
    if (dateDisplay) {
        // Use explicit date formatting to ensure correct display
        const today = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.textContent = today.toLocaleDateString('en-US', options);
        console.log("Date set to:", dateDisplay.textContent);
    }

    // Initialize weekly mood review
    initializeWeeklyMoodReview();

    // Add credit system UI elements if they don't exist
    const submissionStatsEl = document.querySelector('.submission-stats');
    if (!submissionStatsEl) {
        // Find a good place to add the submission counter (near the form)
        const formContainer = document.getElementById("story-form");
        
        if (formContainer) {
            const statsElement = document.createElement('div');
            statsElement.className = 'submission-stats';
            statsElement.innerHTML = `
                <div id="submission-counter" class="submission-counter">
                    ${maxDailyFreeSubmissions} free entries left today
                </div>
                <div id="credits-info" class="credits-info">
                    You've used all free entries. Each additional entry costs 1 credit.
                </div>
            `;
            
            // Insert before the form
            formContainer.parentNode.insertBefore(statsElement, formContainer);
            
            // Add styling
            const styleElement = document.createElement('style');
            styleElement.textContent = `
                .submission-stats {
                    margin-bottom: 15px;
                    font-size: 0.9rem;
                }
                
                .submission-counter {
                    display: inline-block;
                    padding: 5px 10px;
                    border-radius: 4px;
                    background-color: #e8f5e9;
                    color: #2e7d32;
                }
                
                .submission-counter.warning {
                    background-color: #ffecb3;
                    color: #ff6f00;
                }
                
                .credits-info {
                    margin-top: 8px;
                    color: #757575;
                    display: none;
                    font-style: italic;
                }
                
                .credits-info.visible {
                    display: block;
                }
                
                #reward-points {
                    transition: all 0.3s ease;
                }
                
                .rewards-increased {
                    animation: pulse-green 1.5s ease;
                }
                
                .rewards-decreased {
                    animation: pulse-red 1.5s ease;
                }
                
                #submit-story.disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }
                
                @keyframes pulse-green {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.2); color: #4CAF50; }
                    100% { transform: scale(1); }
                }
                
                @keyframes pulse-red {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.2); color: #f44336; }
                    100% { transform: scale(1); }
                }
            `;
            document.head.appendChild(styleElement);
        }
    }
    
    // Add event listener to button click
    submitButton.addEventListener("click", function(event) {
        // Prevent any default action that might cause page refresh
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        // Prevent duplicate processing
        if (isStoryProcessing) {
            console.log("Submission already in progress. Ignoring duplicate.");
            return;
        }
        
        // Manually validate input
        if (!storyInput.value.trim()) {
            alert("⚠️ Please enter your story!");
            return;
        }
        
        // Get current values with safety checks
        const currentDailyCount = typeof dailyStoryCount !== 'undefined' ? dailyStoryCount : 0;
        const currentRewards = typeof rewards !== 'undefined' ? rewards : 5;
        const maxFreeSubmissions = typeof maxDailyFreeSubmissions !== 'undefined' ? maxDailyFreeSubmissions : 2;
        
        // Check if user has used all free entries and has no credits
        if (currentDailyCount >= maxFreeSubmissions && currentRewards <= 0) {
            alert("❌ You have 0 credits remaining and have used all free entries today.");
            // Show notification in the UI as well
            if (moodDisplay) moodDisplay.textContent = "Mood: Not Available"; 
            if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: You have no credits left. Come back tomorrow for free entries or earn more credits.";
            return;
        }
        
        // Process the story and set guard
        isStoryProcessing = true;
        processStory(storyInput.value.trim())
            .catch(error => console.error(error))
            .finally(() => { isStoryProcessing = false; });
    });
    
    // Also prevent the entire form from submitting if the container is still a form
    if (storyFormContainer.tagName === "FORM") {
        storyFormContainer.addEventListener("submit", function(event) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        });
    }
    
    // Function to fetch user rewards from the server
    async function fetchUserRewards() {
        try {
            // Use the config object to get API URL
            console.log("Fetching user rewards data from server...");
            const response = await fetchWithAuth(config.getUrl('userRewards'));
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("User rewards data from server:", data);
            
            if (data === null || typeof data !== 'object') {
                console.error("Invalid data received from server:", data);
                throw new Error("Invalid data format received from server");
            }
            
            // Validate received data values
            const receivedRewards = typeof data.rewards === 'number' ? data.rewards : 0;
            const receivedDailyCount = typeof data.daily_count === 'number' ? data.daily_count : 0;
            
            console.log("Validated data - rewards:", receivedRewards, "daily_count:", receivedDailyCount);
            
            // Update local variables with server data
            rewards = receivedRewards;
            dailyStoryCount = receivedDailyCount;
            
            // Force-refresh the UI calculations
            const freeSubmissionsLeft = Math.max(0, maxDailyFreeSubmissions - dailyStoryCount);
            console.log("Calculated free submissions left:", freeSubmissionsLeft);
            
            // Update UI with received values
            updateRewardPoints(rewards);
            
            // Update submission counters in UI
            // updateSubmissionCounters(); // MODIFIED: Commented out, updateUIBasedOnUserData below handles it
            
            console.log("Updated from server - Daily story count:", dailyStoryCount, "Rewards:", rewards);
            userDataLoaded = true;
            
            // Central point for UI updates after fetching data
            updateUIBasedOnUserData(); 
            
        } catch (error) {
            console.error("Error fetching user rewards:", error);
            // If we can't fetch from server, we'll keep the default values
            userDataLoaded = true; // Set to true even on error so UI isn't blocked
            updateUIBasedOnUserData(); // MODIFIED: Call updateUIBasedOnUserData even on error to reflect default/current state
        }
    }
    
    // Function to update user rewards on the server
    async function updateServerRewards(newRewards) {
        try {
            // Use the config object to get API URL
            const response = await fetchWithAuth(config.getUrl('userRewards'), {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ rewards: newRewards })
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("Server rewards update response:", data);
            return true;
            
        } catch (error) {
            console.error("Error updating rewards on server:", error);
            return false;
        }
    }
    
    // Function to increment daily count on server
    async function incrementDailyCount() {
        try {
            // Use the config object to get API URL
            console.log("Incrementing daily story count, current value:", dailyStoryCount);
            const response = await fetchWithAuth(config.getUrl('userDailyCount'), {
                method: "POST"
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("Server daily count update response:", data);
            
            // Ensure we get a valid number back
            if (data && typeof data.daily_count === 'number') {
                dailyStoryCount = data.daily_count;
                console.log("Updated dailyStoryCount to:", dailyStoryCount);
                
                // Force UI update after count changes
                updateUIBasedOnUserData(); 
            } else {
                // If server doesn't return a proper count, increment locally as fallback
                dailyStoryCount++;
                console.log("Server didn't return valid count, incremented locally to:", dailyStoryCount);
                updateUIBasedOnUserData(); // MODIFIED: Ensure UI updates on local fallback increment
            }
            
            return true;
            
        } catch (error) {
            console.error("Error incrementing daily count on server:", error);
            // As a fallback, increment locally
            dailyStoryCount++;
            console.log("Error from server, incremented count locally to:", dailyStoryCount);
            
            // Force UI update
            updateUIBasedOnUserData(); 
            return false;
        }
    }
    
    // ======== Separated story processing into its own function ========
    async function processStory(storyText) {
        // Make sure user data is loaded before proceeding
        if (!userDataLoaded) {
            console.log("User data not loaded yet, fetching now...");
            await fetchUserRewards();
        }
        
        // Validate content first
        if (!storyText || !storyText.trim()) {
            moodDisplay.textContent = "Mood: Error!";
            feedbackDisplay.textContent = "Feedback: Please enter some text before submitting.";
            return;
        }
        
        // Double-check credit situation - this ensures we don't process if a race condition 
        // occurred between when the button was clicked and when processing started
        const currentDailyCount = typeof dailyStoryCount !== 'undefined' ? dailyStoryCount : 0;
        const currentRewards = typeof rewards !== 'undefined' ? rewards : 5;
        const maxFreeSubmissions = typeof maxDailyFreeSubmissions !== 'undefined' ? maxDailyFreeSubmissions : 2;
        
        if (currentDailyCount >= maxFreeSubmissions && currentRewards <= 0) {
            console.log("No credits available for processing - aborting");
            if (moodDisplay) moodDisplay.textContent = "Mood: Not Available"; 
            if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: You have no credits left. Come back tomorrow for free entries or earn more credits.";
            isStoryProcessing = false;
            return;
        }

        // Determine if this is a free or paid submission
        let isPaidSubmission = false;
        let creditsToAdd = 0; // Default to not changing credits
        
        if (dailyStoryCount >= maxDailyFreeSubmissions) {
            // After free submissions are used, check if they can pay with credits
            isPaidSubmission = true;
            console.log("Free submissions used up, checking credits");
            
            // Check if they have enough credits
            if (rewards <= 0) {
                // Show error and reset display with a more meaningful message
                if (moodDisplay) moodDisplay.textContent = "Mood: Not Available"; 
                if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: You have no credits left. Come back tomorrow for free entries or earn more credits.";
                updateRewardPoints(0); // Ensure displayed as 0
                alert("❌ You have 0 credits remaining and have used all free entries today.");
                isStoryProcessing = false; // Reset processing flag
                return; // Stop execution
            }
            
            // Will deduct 1 credit when processing completes successfully
            creditsToAdd = -1;
        }
        
        // Show loading state - ensure these elements exist before updating
        if (moodDisplay) {
            moodDisplay.textContent = "Mood: Analyzing...";
            moodDisplay.classList.add('loading');
            // Reset any previous display styles
            moodDisplay.style.color = ''; 
        }
        if (feedbackDisplay) {
            feedbackDisplay.textContent = "Feedback: Please wait...";
            feedbackDisplay.classList.add('loading');
            // Reset any previous display styles
            feedbackDisplay.style.color = '';
        }
        
        // Animate the loading state to draw attention
        animateResults();

        // Show the global loading indicator
        loadingUtils.show("Analyzing your story...");
        
        // Variables for retry logic
        let attempts = 0;
        const maxAttempts = 3;
        let result, response;
        
        // Function to clear loading states if something goes wrong
        const clearLoadingStates = () => {
            loadingUtils.hide();
            if (moodDisplay) moodDisplay.classList.remove('loading');
            if (feedbackDisplay) feedbackDisplay.classList.remove('loading');
        };
        
        while (attempts < maxAttempts) {
            attempts++;
            
            try {
                console.log(`📤 Sending story for analysis (attempt ${attempts})...`);
                
                // Use a fetch with a timeout to prevent hanging
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
                
                // Use the config object to get the analyze API URL
                // Ensure existing results are cleared to prevent flickering
                if (moodDisplay) moodDisplay.textContent = "Mood: Analyzing...";
                if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: Please wait...";
                
                response = await fetchWithAuth(config.getUrl('analyze'), {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ 
                        story: storyText,
                        timestamp: new Date().getTime() // Add timestamp to prevent caching
                    }),
                    signal: controller.signal
                });
                
                // Always clear the timeout
                clearTimeout(timeoutId);
                
                console.log("🚀 Response status:", response.status);
                
                // Check if the response is OK before trying to parse JSON
                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                
                result = await response.json();
                console.log("🔍 Parsed JSON response:", result);
                
                // Verify response has the required fields
                if (!result || !result.mood || !result.feedback) {
                    console.error("Invalid response format - missing required fields");
                    if (attempts >= maxAttempts) {
                        throw new Error("Server returned incomplete response after multiple attempts");
                    }
                    // Try again if we don't have a complete response
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    continue;
                }
                
                // If we get here, we succeeded, so break out of retry loop
                break;
                
            } catch (fetchError) {
                if (fetchError.name === 'AbortError') {
                    console.error("Fetch request timed out");
                    
                    if (attempts >= maxAttempts) {
                        clearLoadingStates();
                        if (moodDisplay) moodDisplay.textContent = "Mood: Server timeout";
                        if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: The server took too long to respond. Try again later.";
                        return;
                    }
                    
                    console.log(`Retrying after timeout (attempt ${attempts})...`);
                    continue; // Try again
                    
                } else if (fetchError.message.includes("Authentication failed")) {
                    // Authentication error - handled separately
                    clearLoadingStates();
                    if (moodDisplay) moodDisplay.textContent = "Mood: Authentication Error!";
                    if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: Your session has expired. Please log in again.";
                    tokenManager.showLoginExpired();
                    return;
                } else if (attempts < maxAttempts) {
                    // Network error, but we can retry
                    console.log(`Network error, retrying (attempt ${attempts})...`);
                    // Wait a moment before retrying (increasing delay with each attempt)
                    await new Promise(resolve => setTimeout(resolve, attempts * 1000));
                    continue; // Try again
                } else {
                    // Show error message in the UI instead of throwing which could break the UI
                    clearLoadingStates();
                    console.error("Fetch error after all retries:", fetchError);
                    if (moodDisplay) moodDisplay.textContent = "Mood: Connection Error";
                    if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: Unable to reach the server. Please check your connection and try again.";
                    return;
                }
            }
        }

        // Hide loading overlay
        loadingUtils.hide();
        
        // Remove loading classes
        if (moodDisplay) moodDisplay.classList.remove('loading');
        if (feedbackDisplay) feedbackDisplay.classList.remove('loading');

        // Update UI with the results - with extra safety checks
        if (result && result.mood && result.feedback) {
            // Update mood and feedback display with animation
            if (moodDisplay) {
                moodDisplay.textContent = `Mood: ${result.mood}`;
                moodDisplay.style.fontWeight = "bold";
            }
            
            if (feedbackDisplay) {
                feedbackDisplay.textContent = `Feedback: ${result.feedback}`;
                feedbackDisplay.style.fontWeight = "bold";
            }
            
            console.log("Updated mood and feedback displays");
            
            // Always increment daily count on successful submission
            await incrementDailyCount();
            console.log("Updated daily story count on server:", dailyStoryCount);
            
            // Apply credit changes for paid submissions
            if (isPaidSubmission && creditsToAdd !== 0) {
                // Extra safety check - don't deduct if already at 0
                if (rewards <= 0 && creditsToAdd < 0) {
                    console.error("Attempted to use credits when none available");
                    if (moodDisplay) moodDisplay.textContent = "Mood: Credit Error";
                    if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: No credits available for this submission.";
                    return;
                }
                
                const oldRewards = rewards;
                rewards = Math.max(0, rewards + creditsToAdd); // Ensure never below 0
                console.log("Updating rewards to:", rewards);
                
                // Update rewards on the server
                await updateServerRewards(rewards);
                
                // Animate the reward points change
                updateRewardPoints(rewards, true);
            } else {
                // Just update UI without animation
                updateRewardPoints(rewards);
            }
            
            // Update submission counters with the new daily count
            console.log("After story process - updating UI with dailyStoryCount:", dailyStoryCount);
            updateUIBasedOnUserData(); 
            
            // Ensure the results are visible by scrolling to them
            moodDisplay.scrollIntoView({ behavior: "smooth", block: "center" });
            
            // Show a subtle notification about credits if this was a paid submission
            if (isPaidSubmission) {
                showCreditNotification(creditsToAdd);
            }

            // Save mood data to server for weekly review
            await saveWeeklyMoodData(result.mood);
            
            // Update weekly review after adding new data
            await fetchAndDisplayWeeklyMoodData();
            
            // Clear input field after successful submission
            storyInput.value = "";
            
            // Save results to storage using tokenManager
            tokenManager.saveMoodData(result.mood, result.feedback);
            
        } else if (result && result.error) {
            if (moodDisplay) moodDisplay.textContent = "Mood: Error!";
            if (feedbackDisplay) feedbackDisplay.textContent = `Feedback: ${result.error}`;
            console.error("Backend error:", result.error);
        } else {
            if (moodDisplay) moodDisplay.textContent = "Mood: Response Error";
            if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: Could not analyze your story. Please try again.";
            console.error("Invalid response format from server");
        }
    }

    // New function to save weekly mood data to the server
    async function saveWeeklyMoodData(mood) {
        try {
            // Use the actual current date and ensure correct day name
            const today = new Date();
            // Get both short and full weekday names to avoid any display issues
            const dayName = today.toLocaleDateString('en-US', { weekday: 'short' });
            const fullDayName = today.toLocaleDateString('en-US', { weekday: 'long' });
            
            const dayIndex = today.getDay(); // 0=Sunday, 1=Monday, etc.
            console.log("Saving mood data for today:", fullDayName, "(", dayName, "), day index:", dayIndex);
            
            const response = await fetchWithAuth(config.getUrl('userWeeklyMood'), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    mood: mood,
                    date: today.toISOString(),
                    dayName: dayName,
                    fullDayName: fullDayName,
                    dayIndex: dayIndex // Add day index (0=Sunday, 1=Monday, etc.) for reliable matching
                })
            });

            if (!response.ok) {
                console.error("Failed to save weekly mood data");
            }
        } catch (error) {
            console.error("Error saving weekly mood data:", error);
        }
    }

    // Function to fetch weekly mood data from the server
    async function fetchAndDisplayWeeklyMoodData() {
        const weeklyReview = document.getElementById("weekly-review");
        if (!weeklyReview) return; // Safety check

        try {
            // Show loading indicator for better user experience
            weeklyReview.innerHTML = `<div class="loading-indicator">Loading your weekly mood data...</div>`;
            
            // Use the withLoading utility for a consistent loading experience
            const response = await loadingUtils.withLoading(
                fetchWithAuth(config.getUrl('userWeeklyMood'), { showErrorToasts: true }),
                "Loading mood data..."
            );

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            const data = await response.json();
            const weeklyData = data.weekly_data || [];

            if (weeklyData.length > 0) {
                console.log("Weekly mood data from server:", weeklyData);
                displayWeeklyMoodReview(weeklyData, weeklyReview);
            } else {
                weeklyReview.innerHTML = `
                    <div class="empty-state">
                        <p>No data yet. Start journaling to see your weekly mood patterns!</p>
                        <button id="refresh-weekly-data" class="refresh-btn">Refresh Data</button>
                    </div>`;
                
                // Add refresh button handler
                document.getElementById("refresh-weekly-data")?.addEventListener("click", () => {
                    fetchAndDisplayWeeklyMoodData();
                });
            }
        } catch (error) {
            console.error("Error fetching weekly mood data:", error);
            
            // Show a more user-friendly error with a retry button
            weeklyReview.innerHTML = `
                <div class="error-state">
                    <p>Unable to load weekly review data.</p>
                    <button id="retry-weekly-data" class="retry-btn">Try Again</button>
                </div>`;
            
            // Add retry button handler
            document.getElementById("retry-weekly-data")?.addEventListener("click", () => {
                fetchAndDisplayWeeklyMoodData();
            });
        }
    }

    // Function to initialize weekly mood review
    function initializeWeeklyMoodReview() {
        // Only call the server data function - removed redundant initializeWeeklyMoodVisualization call
        fetchAndDisplayWeeklyMoodData();
    }

    // Function to restore results from storage
    function restoreResultsFromStorage() {
        const moodData = tokenManager.getMoodData();
        
        if (moodData.mood && moodDisplay) {
            moodDisplay.textContent = `Mood: ${moodData.mood}`;
            moodDisplay.style.fontWeight = "bold";
        } else {
            // Reset display if no data
            if (moodDisplay) moodDisplay.textContent = "Mood: --";
        }

        if (moodData.feedback && feedbackDisplay) {
            feedbackDisplay.textContent = `Feedback: ${moodData.feedback}`;
            feedbackDisplay.style.fontWeight = "bold";
        } else {
            // Reset display if no data
            if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: --";
        }
    }

    // Check if we have cached mood data to display
    const cachedMoodData = tokenManager.getMoodData();
    if (cachedMoodData.mood && cachedMoodData.feedback) {
        moodDisplay.textContent = `Mood: ${cachedMoodData.mood}`;
        feedbackDisplay.textContent = `Feedback: ${cachedMoodData.feedback}`;
        
        // Add animation to the results when restoring from cache
        animateResults();
    }

    // Function to animate results
    function animateResults() {
        // Clear any existing classes
        moodDisplay.classList.remove('fade-in-up');
        feedbackDisplay.classList.remove('fade-in-up');
        
        // Trigger reflow
        void moodDisplay.offsetWidth;
        void feedbackDisplay.offsetWidth;
        
        // Add animation classes
        moodDisplay.classList.add('fade-in-up');
        feedbackDisplay.classList.add('fade-in-up');
        
        // Add CSS for animations if not already present
        if (!document.getElementById('dashboard-animations')) {
            const styleElement = document.createElement('style');
            styleElement.id = 'dashboard-animations';
            styleElement.textContent = `
                @keyframes fadeInUp {
                    from { 
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                @keyframes pulse {
                    0% { opacity: 0.6; }
                    50% { opacity: 1; }
                    100% { opacity: 0.6; }
                }
                
                .fade-in-up {
                    animation: fadeInUp 0.5s ease forwards;
                }
                
                #mood-display, #feedback-display {
                    transform: translateY(0); /* Reset transform */
                    transition: all 0.3s ease;
                    position: relative;
                    min-height: 24px;
                }
                
                #mood-display.loading, #feedback-display.loading {
                    animation: pulse 1.5s infinite ease-in-out;
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                    padding-left: 5px;
                    padding-right: 5px;
                }
                
                #mood-display.loading::after, #feedback-display.loading::after {
                    content: '';
                    position: absolute;
                    bottom: -3px;
                    left: 0;
                    width: 100%;
                    height: 2px;
                    background: linear-gradient(to right, transparent, var(--primary-color), transparent);
                    animation: loading-bar 2s infinite ease-in-out;
                }
                
                @keyframes loading-bar {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
                
                #mood-display:hover, #feedback-display:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
                }
                
                .results-section h3 {
                    position: relative;
                    display: inline-block;
                    margin-bottom: 20px;
                }
                
                .results-section h3:after {
                    content: '';
                    position: absolute;
                    width: 0;
                    height: 2px;
                    bottom: -5px;
                    left: 0;
                    background-color: var(--primary-color);
                    transition: width 0.5s ease;
                }
                
                .results-section:hover h3:after {
                    width: 100%;
                }
            `;
            document.head.appendChild(styleElement);
        }
    }

    // Hide the loading overlay after a short delay (simulating initial load)
    setTimeout(function() {
        if (loadingOverlay) {
            loadingOverlay.classList.remove('active');
        }
        
        // Initialize weekly mood visualization
        initializeWeeklyMoodVisualization();
        
        // Validate UI state is consistent with data
        validateUIState();
        
        // Set up periodic UI validation to catch any race conditions
        // This ensures the display always matches the actual data state
        setInterval(validateUIState, 3000); // Check every 3 seconds
    }, 300);

    // Function to initialize weekly mood visualization
    function initializeWeeklyMoodVisualization() {
        const weeklyReviewElement = document.getElementById('weekly-review');
        if (!weeklyReviewElement) return;
        
        // Don't use sample data, rely on actual server data instead
        // Let the server API handle mood data retrieval
        console.log("Weekly mood visualization initialization deferred to server data");
        
        // Don't create visualization here - it will be handled by fetchAndDisplayWeeklyMoodData
    }

    // Function to create weekly mood visualization with chart
    function createWeeklyMoodVisualization(weeklyMoods, container) {
        // Get mood counts
        const moodCounts = {};
        Object.values(weeklyMoods).forEach(mood => {
            if (mood) {
                moodCounts[mood] = (moodCounts[mood] || 0) + 1;
            }
        });
        
        // Count days with data
        const daysWithData = Object.values(weeklyMoods).filter(mood => mood).length;
        
        // Only show visualization if we have data
        if (daysWithData === 0) {
            container.innerHTML = `
                <div class="no-data-message">
                    <p>No mood data for this week yet. Submit your daily story to see your mood trends.</p>
                </div>
            `;
            return;
        }
        
        // Create HTML for the visualization
        const html = `
            <div class="weekly-review-container">
                <div class="mood-summary">
                    <h4>This Week's Summary</h4>
                    <span>${daysWithData} days tracked</span>
                </div>
                
                <div class="mood-distribution">
                    ${Object.entries(moodCounts).map(([mood, count]) => {
                        const percentage = Math.round((count / daysWithData) * 100);
                        return `
                            <div class="mood-bar">
                                <div class="mood-label">${mood}</div>
                                <div class="mood-progress">
                                    <div class="mood-fill" style="width: ${percentage}%"></div>
                                </div>
                                <div class="mood-percentage">${percentage}%</div>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <h4>Daily Mood</h4>
                <div class="daily-moods">
                    ${['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(day => {
                        const mood = weeklyMoods[day] || '';
                        const hasData = mood !== '';
                        const moodClass = getMoodColorClass(mood);
                        
                        return `
                            <div class="day-mood ${!hasData ? 'no-data' : ''}">
                                <div class="day-label">${day.substring(0, 3)}</div>
                                <div class="mood-indicator ${moodClass}"></div>
                                <div class="day-mood-value">${hasData ? mood : 'No data'}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="review-insights">
                    <h4>Insights</h4>
                    <p>${generateInsightMessage(moodCounts, daysWithData)}</p>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Add animation
        const reviewContainer = container.querySelector('.weekly-review-container');
        if (reviewContainer) {
            setTimeout(() => reviewContainer.classList.add('fade-in-up'), 100);
        }
        
        // Add CSS for the visualization
        if (!document.getElementById('mood-visualization-styles')) {
            const styleElement = document.createElement('style');
            styleElement.id = 'mood-visualization-styles';
            styleElement.textContent = `
                .mood-indicator {
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    margin: 5px auto;
                }
                
                .mood-color-happy {
                    background-color: #4CAF50;
                }
                
                .mood-color-excited {
                    background-color: #2196F3;
                }
                
                .mood-color-neutral {
                    background-color: #FFC107;
                }
                
                .mood-color-sad {
                    background-color: #9C27B0;
                }
                
                .mood-color-angry {
                    background-color: #F44336;
                }
                
                .no-data-message {
                    text-align: center;
                    padding: 20px;
                    color: var(--text-muted);
                }
                
                .weekly-review-container {
                    opacity: 0;
                    transform: translateY(20px);
                    transition: opacity 0.5s ease, transform 0.5s ease;
                }
                
                .weekly-review-container.fade-in-up {
                    opacity: 1;
                    transform: translateY(0);
                }
                
                .review-insights {
                    margin-top: 20px;
                    padding: 15px;
                    border-radius: 8px;
                    background-color: rgba(76, 175, 80, 0.1);
                }
                
                .review-insights h4 {
                    margin-top: 0;
                    color: var(--secondary-color);
                }
                
                .daily-moods {
                    display: flex;
                    justify-content: space-between;
                    margin: 15px 0;
                }
            `;
            document.head.appendChild(styleElement);
        }
    }

    // Helper function to get color class based on mood
    function getMoodColorClass(mood) {
        const moodLower = (mood || '').toLowerCase();
        if (moodLower.includes('happy')) return 'mood-color-happy';
        if (moodLower.includes('excit')) return 'mood-color-excited';
        if (moodLower.includes('neutr') || moodLower.includes('normal')) return 'mood-color-neutral';
        if (moodLower.includes('sad') || moodLower.includes('depress')) return 'mood-color-sad';
        if (moodLower.includes('ang') || moodLower.includes('mad')) return 'mood-color-angry';
        return '';
    }

    // Helper function to generate insight message
    function generateInsightMessage(moodCounts, daysWithData) {
        // Find dominant mood
        let dominantMood = '';
        let maxCount = 0;
        
        Object.entries(moodCounts).forEach(([mood, count]) => {
            if (count > maxCount) {
                dominantMood = mood;
                maxCount = count;
            }
        });
        
        const dominantPercentage = Math.round((maxCount / daysWithData) * 100);
        
        // Generate insight based on dominant mood
        if (dominantMood.toLowerCase().includes('happy') || dominantMood.toLowerCase().includes('excit')) {
            return `You've been feeling ${dominantMood.toLowerCase()} ${dominantPercentage}% of the time this week. Keep up the positive energy!`;
        } else if (dominantMood.toLowerCase().includes('neutr') || dominantMood.toLowerCase().includes('normal')) {
            return `Your mood has been mostly neutral this week (${dominantPercentage}%). Consider activities that bring you joy!`;
        } else if (dominantMood.toLowerCase().includes('sad') || dominantMood.toLowerCase().includes('depress')) {
            return `You've been feeling down ${dominantPercentage}% of the week. Remember to take care of yourself and consider talking with someone you trust.`;
        } else {
            return `Your most common mood this week was ${dominantMood.toLowerCase()} (${dominantPercentage}%). Tracking your moods helps build self-awareness.`;
        }
    }

    // Update weekly mood data
    function updateWeeklyMoodData(mood) {
        if (!mood) return;
        
        // Get day of week
        const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const today = dayNames[new Date().getDay()]; // FIXED: Corrected syntax error: removed dot before new
        
        // Get current weekly data
        let weeklyMoods = JSON.parse(sessionStorage.getItem('weeklyMoods') || '{}');
        
        // Update today's mood
        weeklyMoods[today] = mood;
        
        // Store updated data
        sessionStorage.setItem('weeklyMoods', JSON.stringify(weeklyMoods));
        
        // Refresh visualization
        const weeklyReviewElement = document.getElementById('weekly-review');
        if (weeklyReviewElement) {
            createWeeklyMoodVisualization(weeklyMoods, weeklyReviewElement);
        }
    }
});

// Function to update reward points in the navbar
function updateRewardPoints(value, animate = false) {
    // Update both in dashboard and navbar if they exist
    const rewardPoints = document.getElementById("reward-points");
    if (rewardPoints) {
        // Get current value to determine if this is an increase or decrease
        const currentValue = parseInt(rewardPoints.textContent || "0");
        
        // Set new value
        rewardPoints.textContent = value;
        console.log("Updated reward points:", value);
        
        // Animate if requested and there's a change
        if (animate && currentValue !== value) {
            // Remove existing animation classes
            rewardPoints.classList.remove('rewards-increased', 'rewards-decreased');
            
            // Add appropriate animation class
            if (value > currentValue) {
                rewardPoints.classList.add('rewards-increased');
            } else if (value < currentValue) {
                rewardPoints.classList.add('rewards-decreased');
            }
            
            // Remove animation class after it completes
            setTimeout(() => {
                rewardPoints.classList.remove('rewards-increased', 'rewards-decreased');
            }, 1500);
        }
    }
    
    // MODIFIED: Centralize UI update through updateUIBasedOnUserData
    updateUIBasedOnUserData();
}

// Function to validate and ensure UI state is consistent
function validateUIState() {
    // MODIFIED: Add guard for userDataLoaded
    if (!userDataLoaded) {
        console.log("validateUIState called before user data loaded. Skipping validation.");
        return;
    }

    // Ensure the submission counter reflects the actual dailyStoryCount
    const submissionCounterEl = document.getElementById("submission-counter");
    const freeSubmissionsLeft = Math.max(0, maxDailyFreeSubmissions - dailyStoryCount);
    
    if (submissionCounterEl && 
        submissionCounterEl.textContent !== `${freeSubmissionsLeft} free entries left today`) {
        console.log("UI inconsistency detected! Fixing submission counter.");
        console.log("Expected:", `${freeSubmissionsLeft} free entries left today`);
        console.log("Actual:", submissionCounterEl.textContent);
        
        submissionCounterEl.textContent = `${freeSubmissionsLeft} free entries left today`;
        
        if (freeSubmissionsLeft === 0) {
            submissionCounterEl.classList.add("warning");
        } else {
            submissionCounterEl.classList.remove("warning");
        }
    }
    
    // Update button state to match data
    const submitButton = document.getElementById("submit-story");
    if (submitButton) {
        const shouldBeDisabled = dailyStoryCount >= maxDailyFreeSubmissions && rewards <= 0;
        const isCurrentlyDisabled = submitButton.disabled === true;
        
        if (shouldBeDisabled !== isCurrentlyDisabled) {
            console.log("UI inconsistency detected! Fixing submit button state.");
            console.log("Button should be disabled:", shouldBeDisabled);
            console.log("Button is currently disabled:", isCurrentlyDisabled);
            
            if (shouldBeDisabled) {
                submitButton.disabled = true;
                submitButton.title = "No credits remaining";
                submitButton.classList.add("disabled");
            } else {
                submitButton.disabled = false;
                submitButton.title = "";
                submitButton.classList.remove("disabled");
            }
        }
    }
}

// Function to update submit button state based on user's credit situation
function updateSubmitButtonState() {
    const submitButton = document.getElementById("submit-story");
    if (!submitButton) return;
    
    // Ensure variables are defined with default values if not set
    // These should reflect the true current state after any server updates
    const currentDailyCount = typeof dailyStoryCount !== 'undefined' ? dailyStoryCount : 0;
    const currentRewards = typeof rewards !== 'undefined' ? rewards : 0; // Default to 0 if undefined
    const currentMaxFreeSubmissions = typeof maxDailyFreeSubmissions !== 'undefined' ? maxDailyFreeSubmissions : 2;
    
    const canSubmit = (currentDailyCount < currentMaxFreeSubmissions) || (currentRewards > 0);
    const reason = (currentDailyCount >= currentMaxFreeSubmissions && currentRewards <= 0) ? "No free entries or credits left." : "";

    console.log(
        "updateSubmitButtonState - dailyStoryCount:", currentDailyCount, 
        "maxDailyFreeSubmissions:", currentMaxFreeSubmissions,
        "rewards:", currentRewards,
        "canSubmit:", canSubmit,
        "Reason:", reason
    );
    
    if (canSubmit) {
        submitButton.disabled = false;
        submitButton.title = ""; // Clear any previous "disabled" title
        submitButton.classList.remove("disabled");
        
        // Remove warning message if it exists
        const warningMsg = document.querySelector('.credits-warning');
        if (warningMsg) warningMsg.remove();

    } else {
        submitButton.disabled = true;
        submitButton.title = reason || "No credits remaining"; // Default title
        submitButton.classList.add("disabled");
        
        // Show warning message near the form
        let warningMsg = document.querySelector('.credits-warning');
        if (!warningMsg) {
            warningMsg = document.createElement('div');
            warningMsg.className = 'credits-warning';
            warningMsg.style.color = '#f44336'; // Consider using CSS variables
            warningMsg.style.fontWeight = 'bold';
            warningMsg.style.marginBottom = '15px';
            
            const storyFormContainer = document.getElementById("story-form");
            if (storyFormContainer) {
                storyFormContainer.parentNode.insertBefore(warningMsg, storyFormContainer);
            }
        }
        warningMsg.innerHTML = reason || 'You have no more free entries or credits today. Come back tomorrow for more free entries!';
    }
}

// Function to show a credit notification
function showCreditNotification(creditsChange) {
    // Create a notification element
    const notification = document.createElement('div');
    notification.className = 'credit-notification';
    
    if (creditsChange < 0) {
        notification.innerHTML = `<span class="credit-used">-1 credit used</span>`;
        notification.classList.add('credit-decrease');
    } else if (creditsChange > 0) {
        notification.innerHTML = `<span class="credit-earned">+${creditsChange} credit earned</span>`;
        notification.classList.add('credit-increase');
    }
    
    // Add to document
    document.body.appendChild(notification);
    
    // Add CSS for notifications if not already present
    if (!document.getElementById('credit-notification-styles')) {
        const styleElement = document.createElement('style');
        styleElement.id = 'credit-notification-styles';
        styleElement.textContent = `
            .credit-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: rgba(0, 0, 0, 0.7);
                color: #fff;
                padding: 10px 15px;
                border-radius: 5px;
                z-index: 1000;
                opacity: 0;
                transform: translateY(-20px);
                animation: notification-appear 3s ease forwards;
            }
            
            .credit-decrease {
                border-left: 4px solid #f44336;
            }
            
            .credit-increase {
                border-left: 4px solid #4CAF50;
            }
            
            .credit-used {
                color: #ff7875;
            }
            
            .credit-earned {
                color: #52c41a;
            }
            
            @keyframes notification-appear {
                0% { opacity: 0; transform: translateY(-20px); }
                15% { opacity: 1; transform: translateY(0); }
                85% { opacity: 1; transform: translateY(0); }
                100% { opacity: 0; transform: translateY(-20px); }
            }
        `;
        document.head.appendChild(styleElement);
    }
    
    // Remove after animation completes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Function to display weekly mood data with improved visualization
function displayWeeklyMoodReview(weeklyData, container) {
    // Get only the last 7 days of data
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    
    const weekData = weeklyData.filter(entry => new Date(entry.date) >= oneWeekAgo);
    
    // Handle empty dataset gracefully
    if (weekData.length === 0) {
        container.innerHTML = `
            <div class="weekly-review-container empty-state">
                <h4>Weekly Mood Overview</h4>
                <div class="empty-state-message">
                    <p>No mood data recorded this week.</p>
                    <p>Start journaling to see your weekly mood patterns!</p>
                </div>
            </div>
        `;
        return;
    }
    
    // Group entries by day with better date handling
    const dailyMoods = {};
    weekData.forEach(entry => {
        // Parse the entry date
        const entryDate = new Date(entry.date);
        
        // Use the dayIndex from the backend if available (most reliable source)
        // Otherwise calculate from the date (which could have timezone issues)
        const dayIndex = entry.dayIndex !== undefined ? entry.dayIndex : entryDate.getDay();
        
        // Get standardized day key for reliable matching
        const standardDaysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        const day = standardDaysOfWeek[dayIndex];
        
        console.log("Processing entry with date:", entryDate.toDateString(), 
                    "Day index:", dayIndex, 
                    "Day label:", day);
        
        // Store the formatted date for comparing
        const formattedDate = entryDate.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
        
        if (!dailyMoods[day]) {
            dailyMoods[day] = {
                moods: [],
                date: entryDate,
                formattedDate: formattedDate,
                dayIndex: dayIndex
            };
        }
        dailyMoods[day].moods.push(entry.mood);
    });
    
    // Get mood statistics for the whole week
    const moodCounts = {};
    weekData.forEach(entry => {
        moodCounts[entry.mood] = (moodCounts[entry.mood] || 0) + 1;
    });
    
    // Find most frequent mood
    let mostFrequentMood = "Unknown";
    let maxCount = 0;
    
    for (const [mood, count] of Object.entries(moodCounts)) {
        if (count > maxCount) {
            maxCount = count;
            mostFrequentMood = mood;
        }
    }
    
    // Create HTML content with improved styling
    let html = `
        <div class="weekly-review-container">
            <h4>Last 7 Days Overview</h4>
            <div class="mood-summary">
                <div class="mood-summary-item predominant">
                    <span class="summary-label">Predominant mood:</span>
                    <span class="summary-value">${mostFrequentMood}</span>
                </div>
                <div class="mood-summary-item entries">
                    <span class="summary-label">Total entries:</span>
                    <span class="summary-value">${weekData.length}</span>
                </div>
            </div>
            <div class="mood-distribution">
    `;
    
    // Add mood distribution with animation classes
    const moodColors = {
        "happy": "#4CAF50",
        "joy": "#4CAF50",
        "excited": "#2196F3",
        "sadness": "#9C27B0",
        "sad": "#9C27B0",
        "anger": "#F44336",
        "angry": "#F44336",
        "fear": "#FF9800",
        "surprise": "#FF9800",
        "disgust": "#795548",
        "neutral": "#607D8B"
    };
    
    for (const [mood, count] of Object.entries(moodCounts)) {
        const percentage = Math.round((count / weekData.length) * 100);
        // Find matching color or fallback to default
        const moodLower = mood.toLowerCase();
        let barColor = "#607D8B"; // Default gray
        
        // Check for matching mood in our color map
        for (const [key, color] of Object.entries(moodColors)) {
            if (moodLower.includes(key)) {
                barColor = color;
                break;
            }
        }
        
        html += `
            <div class="mood-bar">
                <span class="mood-label">${mood}</span>
                <div class="mood-progress">
                    <div class="mood-fill animate-fill" style="width: 0%; background-color: ${barColor}" data-width="${percentage}%"></div>
                </div>
                <span class="mood-percentage">${percentage}%</span>
            </div>
        `;
    }
    
    html += `
            </div>
            <h4>Daily Breakdown</h4>
            <div class="daily-moods">
    `;
    
    // Use the actual current date
    const currentDate = new Date();
    const todayFormatted = currentDate.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
    
    // Standard order of days for the week (starting with Sunday)
    const standardDaysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    
    // Get the current day index (0 = Sunday, 1 = Monday, etc.)
    const todayIndex = currentDate.getDay();
    
    // Create the last 7 days in correct order
    const last7Days = [];
    console.log("Today's day index:", todayIndex, "which is", standardDaysOfWeek[todayIndex]);
    
    for (let i = 6; i >= 0; i--) {
        // Calculate the day index by going backwards from today
        let dayIndex = (todayIndex - i + 7) % 7; // Ensure positive index
        
        const dayName = standardDaysOfWeek[dayIndex];
        
        // Calculate the date for display in tooltip
        const date = new Date(currentDate);
        date.setDate(currentDate.getDate() - i);
        const fullDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const formattedDate = date.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
        
        console.log("Creating day at position", i, "of 7: day index =", dayIndex, 
                    "day name =", dayName, "date =", date.toDateString());
        
        last7Days.push({
            dayName: dayName,
            fullDate: fullDate,
            formattedDate: formattedDate,
            dayIndex: dayIndex, // Add day index for more reliable day matching
            isToday: i === 0 // Mark today's entry
        });
    }
    
    // Now display each day with the proper labels and improved styling
    for (const dayInfo of last7Days) {
        // Direct mapping by dayName which is based on calculated dayIndex
        const dayMoodData = dailyMoods[dayInfo.dayName];
        
        // Use the direct day mapping
        let dayMoods = [];
        
        if (dayMoodData) {
            dayMoods = dayMoodData.moods;
            console.log("Found mood data for", dayInfo.dayName, "showing", dayMoods.length, "entries", 
                        "day index:", dayInfo.dayIndex, 
                        "is today:", dayInfo.isToday ? "YES" : "NO");
        } else {
            console.log("No mood data found for", dayInfo.dayName, 
                        "day index:", dayInfo.dayIndex, 
                        "is today:", dayInfo.isToday ? "YES" : "NO");
        }
        
        // Fix: Standardize "No entries" text for all days, including Sunday
        let dayMood = dayMoods.length > 0 ? "" : "No entries";
        let moodColor = "#888"; // Default gray for no data
        
        if (dayMoods.length > 0) {
            // Get most frequent mood for the day
            const dayMoodCounts = {};
            dayMoods.forEach(mood => {
                dayMoodCounts[mood] = (dayMoodCounts[mood] || 0) + 1;
            });
            
            const sortedMoods = Object.entries(dayMoodCounts)
                .sort((a, b) => b[1] - a[1]);
            
            dayMood = sortedMoods[0][0];
            
            // Find matching color
            const moodLower = dayMood.toLowerCase();
            for (const [key, color] of Object.entries(moodColors)) {
                if (moodLower.includes(key)) {
                    moodColor = color;
                    break;
                }
            }
        }
        
        const todayClass = dayInfo.isToday ? 'today' : '';
        const dataClass = dayMoods.length === 0 ? 'no-data' : '';
        
        html += `
            <div class="day-mood ${dataClass} ${todayClass}">
                <div class="day-label" title="${dayInfo.fullDate}">${dayInfo.dayName}</div>
                <div class="day-mood-icon">
                    <div class="mood-circle" style="background-color: ${moodColor}"></div>
                </div>
                <div class="day-mood-value">${dayMood}</div>
                <div class="day-mood-count">${dayMoods.length > 0 ? `${dayMoods.length} ${dayMoods.length === 1 ? 'entry' : 'entries'}` : ''}</div>
            </div>
        `;
    }
    
    html += `
            </div>
            <div class="review-insights">
                <h4>Insights</h4>
                <p>${generateInsights(moodCounts, weekData.length)}</p>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Animate the mood bars after they're added to the DOM
    setTimeout(() => {
        document.querySelectorAll('.mood-fill.animate-fill').forEach(bar => {
            const targetWidth = bar.getAttribute('data-width');
            bar.style.width = targetWidth;
        });
    }, 100);
}

// Function to generate insights based on mood data with more varied responses
function generateInsights(moodCounts, totalEntries) {
    if (totalEntries === 0) return "Start journaling to see your mood patterns!";
    
    const moodPercentages = {};
    for (const [mood, count] of Object.entries(moodCounts)) {
        moodPercentages[mood] = Math.round((count / totalEntries) * 100);
    }
    
    const sortedMoods = Object.entries(moodPercentages)
        .sort((a, b) => b[1] - a[1])
        .map(([mood, percentage]) => ({ mood, percentage }));
    
    const primaryMood = sortedMoods[0];
    
    if (sortedMoods.length === 1) {
        return `You've been feeling consistently ${primaryMood.mood.toLowerCase()} this week.`;
    }
    
    const secondaryMood = sortedMoods[1];
    
    // Create more varied responses based on the mood combinations and percentages
    if (primaryMood.percentage > 70) {
        const insightOptions = [
            `Your week has been dominated by ${primaryMood.mood.toLowerCase()} feelings (${primaryMood.percentage}%). Keep tracking to see how your mood evolves.`,
            `You've been predominantly ${primaryMood.mood.toLowerCase()} (${primaryMood.percentage}%) this week. Keep journaling to track your emotional patterns!`,
            `This week's dominant emotion: ${primaryMood.mood} (${primaryMood.percentage}%). Consistent journaling helps you understand your emotional patterns.`
        ];
        return insightOptions[Math.floor(Math.random() * insightOptions.length)];
    } else if (primaryMood.percentage > 50) {
        const insightOptions = [
            `You've been mostly ${primaryMood.mood.toLowerCase()} (${primaryMood.percentage}%), with some ${secondaryMood.mood.toLowerCase()} (${secondaryMood.percentage}%) moments this week.`,
            `This week shows a mix of emotions with ${primaryMood.mood} leading at ${primaryMood.percentage}%, followed by ${secondaryMood.mood} at ${secondaryMood.percentage}%.`,
            `Your emotional landscape this week: primarily ${primaryMood.mood.toLowerCase()} (${primaryMood.percentage}%) with ${secondaryMood.mood.toLowerCase()} (${secondaryMood.percentage}%) as a secondary theme.`
        ];
        return insightOptions[Math.floor(Math.random() * insightOptions.length)];
    } else {
        const insightOptions = [
            `Your mood has been varied this week, with a mix of ${primaryMood.mood.toLowerCase()} (${primaryMood.percentage}%) and ${secondaryMood.mood.toLowerCase()} (${secondaryMood.percentage}%).`,
            `This week shows a diverse emotional pattern: ${primaryMood.mood} (${primaryMood.percentage}%) and ${secondaryMood.mood} (${secondaryMood.percentage}%) are your most common moods.`,
            `You've experienced a balance of different emotions, primarily ${primaryMood.mood.toLowerCase()} (${primaryMood.percentage}%) and ${secondaryMood.mood.toLowerCase()} (${secondaryMood.percentage}%).`
        ];
        return insightOptions[Math.floor(Math.random() * insightOptions.length)];
    }
}

// Function to update all UI elements based on current user data
function updateUIBasedOnUserData() {
    console.log("Central UI Update - dailyStoryCount:", dailyStoryCount, "maxDailyFreeSubmissions:", maxDailyFreeSubmissions, "rewards:", rewards, "userDataLoaded:", userDataLoaded);

    if (!userDataLoaded) {
        console.warn("updateUIBasedOnUserData called before user data was loaded. Deferring UI update.");
        return;
    }

    const submissionCounterEl = document.getElementById("submission-counter");
    const creditsInfoEl = document.getElementById("credits-info");

    // Ensure variables are defined with default values if not set
    const currentDailyCount = typeof dailyStoryCount !== 'undefined' ? dailyStoryCount : 0;
    const currentRewards = typeof rewards !== 'undefined' ? rewards : 0; // Default to 0 if undefined after load
    const currentMaxFreeSubmissions = typeof maxDailyFreeSubmissions !== 'undefined' ? maxDailyFreeSubmissions : 2;

    if (submissionCounterEl) {
        const freeSubmissionsLeft = Math.max(0, currentMaxFreeSubmissions - currentDailyCount);
        submissionCounterEl.textContent = `${freeSubmissionsLeft} free entries left today`;
        if (freeSubmissionsLeft === 0) {
            submissionCounterEl.classList.add("warning");
        } else {
            submissionCounterEl.classList.remove("warning");
        }
    }

    if (creditsInfoEl) {
        if (currentDailyCount >= currentMaxFreeSubmissions) {
            if (currentRewards > 0) {
                creditsInfoEl.textContent = `You've used all free entries. Each additional entry costs 1 credit. You have ${currentRewards} credits.`;
            } else {
                creditsInfoEl.textContent = `You've used all free entries and have no credits left. Come back tomorrow!`;
            }
            creditsInfoEl.classList.add("visible");
        } else {
            creditsInfoEl.classList.remove("visible");
        }
    }
    
    // This function will now solely manage the button's state
    updateSubmitButtonState(); 
}

