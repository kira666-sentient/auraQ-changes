document.addEventListener("DOMContentLoaded", function () {
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

    // Server-side state (will be loaded from API)
    let dailyStoryCount = 0;
    let rewards = 5; // Default until we load from server

    // Load user data from server (rewards and daily count)
    fetchUserRewards();
    
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

    // Add event listener to button click
    submitButton.addEventListener("click", function(event) {
        // Prevent any default action that might cause page refresh
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        // Manually validate input
        if (!storyInput.value.trim()) {
            alert("⚠️ Please enter your story!");
            return;
        }
        
        // Process the story
        processStory(storyInput.value.trim());
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
            const response = await fetchWithAuth(config.getUrl('userRewards'));
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("User rewards data from server:", data);
            
            // Update local variables with server data
            rewards = data.rewards;
            dailyStoryCount = data.daily_count;
            
            // Update UI with received values
            updateRewardPoints(rewards);
            
            console.log("Updated from server - Daily story count:", dailyStoryCount, "Rewards:", rewards);
            
        } catch (error) {
            console.error("Error fetching user rewards:", error);
            // If we can't fetch from server, we'll keep the default values
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
            const response = await fetchWithAuth(config.getUrl('userDailyCount'), {
                method: "POST"
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("Server daily count update response:", data);
            dailyStoryCount = data.daily_count;
            return true;
            
        } catch (error) {
            console.error("Error incrementing daily count on server:", error);
            return false;
        }
    }
    
    // ======== Separated story processing into its own function ========
    async function processStory(storyText) {
        // Show current state before processing
        console.log("Before submission processing:", {
            dailyStoryCount: dailyStoryCount,
            rewards: rewards
        });

        // Block submissions when credits are 0
        if (rewards <= 0) {
            alert("❌ You have 0 credits. Please wait until tomorrow when your credits reset to 5.");
            return; // Stop execution and don't process the submission
        }

        // Check if the user has already submitted the maximum entries for today
        let isPenaltySubmission = false;
        let creditsToAdd = 1; // Default credit reward for normal submissions
        
        if (dailyStoryCount >= 2) {
            alert("⚠️ You've reached the daily limit. -3 credits will be deducted.");
            creditsToAdd = -3; // Penalty deduction
            
            // Calculate new rewards value
            const newRewards = rewards + creditsToAdd;
            
            if (newRewards <= 0) {
                rewards = 0; // Ensure rewards don't go negative
                alert("❌ You now have 0 credits and can't submit more entries today.");
                return; // Stop execution if credits reach 0 after deduction
            }
            
            isPenaltySubmission = true;
        }
        
        // Show loading state - ensure these elements exist before updating
        if (moodDisplay) moodDisplay.textContent = "Mood: Analyzing...";
        if (feedbackDisplay) feedbackDisplay.textContent = "Feedback: Please wait...";

        try {
            console.log("📤 Sending story for analysis:", storyText.substring(0, 30) + "...");
            
            // Use a fetch with a timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            // Use the config object to get the analyze API URL
            let response, result;
            
            try {
                response = await fetchWithAuth(config.getUrl('analyze'), {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ story: storyText }),
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
            } catch (fetchError) {
                if (fetchError.name === 'AbortError') {
                    console.error("Fetch request timed out");
                    moodDisplay.textContent = "Mood: Server timeout";
                    feedbackDisplay.textContent = "Feedback: The server took too long to respond. Try again later.";
                    return;
                } else {
                    throw fetchError;
                }
            }

            // Update UI with the results - with extra safety checks
            if (result && result.mood && result.feedback) {
                // Update mood and feedback display
                moodDisplay.textContent = `Mood: ${result.mood}`;
                moodDisplay.style.fontWeight = "bold";
                
                feedbackDisplay.textContent = `Feedback: ${result.feedback}`;
                feedbackDisplay.style.fontWeight = "bold";
                
                console.log("Updated mood and feedback displays");
                
                // Only increment story count for non-penalty submissions
                if (!isPenaltySubmission) {
                    await incrementDailyCount();
                    console.log("Updated daily story count on server:", dailyStoryCount);
                }
                
                // Apply the rewards change locally
                rewards = rewards + creditsToAdd;
                console.log("Updating rewards to:", rewards);
                
                // Update rewards on the server
                await updateServerRewards(rewards);
                
                // Update UI with new rewards
                updateRewardPoints(rewards);
                
                // Ensure the results are visible by scrolling to them
                moodDisplay.scrollIntoView({ behavior: "smooth", block: "center" });

                // Save mood data to server for weekly review
                await saveWeeklyMoodData(result.mood);
                
                // Update weekly review after adding new data
                await fetchAndDisplayWeeklyMoodData();
                
                // Clear input field after successful submission
                storyInput.value = "";
                
                // Save results to storage using tokenManager
                tokenManager.saveMoodData(result.mood, result.feedback);

            } else if (result && result.error) {
                moodDisplay.textContent = "Mood: Error!";
                feedbackDisplay.textContent = `Feedback: ${result.error}`;
                console.error("Backend error:", result.error);
            } else {
                throw new Error("Invalid response format from server");
            }

        } catch (error) {
            console.error("🔥 Error analyzing story:", error);
            
            if (error.message && error.message.includes("Authentication failed")) {
                moodDisplay.textContent = "Mood: Authentication Error!";
                feedbackDisplay.textContent = "Feedback: Your session has expired. Please log in again.";
                tokenManager.showLoginExpired();
            } else {
                moodDisplay.textContent = "Mood: Connection Error!";
                feedbackDisplay.textContent = "Feedback: Couldn't connect to the server. Please make sure the server is running.";
            }
        }
    }

    // New function to save weekly mood data to the server
    async function saveWeeklyMoodData(mood) {
        try {
            // Use the actual current date and day name with correct formatting
            const today = new Date();
            const dayName = today.toLocaleDateString('en-US', { weekday: 'short' });
            
            const response = await fetchWithAuth(config.getUrl('userWeeklyMood'), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    mood: mood,
                    date: today.toISOString(),
                    dayName: dayName
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
            const response = await fetchWithAuth(config.getUrl('userWeeklyMood'));

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            const data = await response.json();
            const weeklyData = data.weekly_data || [];

            if (weeklyData.length > 0) {
                displayWeeklyMoodReview(weeklyData, weeklyReview);
            } else {
                weeklyReview.innerHTML = `<p>No data yet. Start journaling to see your weekly mood patterns!</p>`;
            }
        } catch (error) {
            console.error("Error fetching weekly mood data:", error);
            weeklyReview.innerHTML = `<p>Failed to load weekly review data. Please try again later.</p>`;
        }
    }

    // Function to initialize weekly mood review
    function initializeWeeklyMoodReview() {
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
});

// Function to update reward points in the navbar
function updateRewardPoints(value) {
    // Update both in dashboard and navbar if they exist
    const rewardPoints = document.getElementById("reward-points");
    if (rewardPoints) {
        rewardPoints.textContent = value;
        console.log("Updated reward points:", value);
    }
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
        // Use the stored dayName if it exists, otherwise calculate from the date
        const entryDate = new Date(entry.date);
        const day = entry.dayName || entryDate.toLocaleDateString('en-US', { weekday: 'short' });
        
        if (!dailyMoods[day]) {
            dailyMoods[day] = {
                moods: [],
                date: entryDate
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
        "joy": "#4CAF50",
        "sadness": "#2196F3",
        "anger": "#F44336",
        "fear": "#9C27B0", 
        "surprise": "#FF9800",
        "disgust": "#795548",
        "neutral": "#607D8B"
    };
    
    for (const [mood, count] of Object.entries(moodCounts)) {
        const percentage = Math.round((count / weekData.length) * 100);
        const barColor = moodColors[mood.toLowerCase()] || "#607D8B"; // Default gray for unknown moods
        
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
    // Standard order of days for the week (starting with Sunday)
    const standardDaysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    
    // Get the current day index (0 = Sunday, 1 = Monday, etc.)
    const todayIndex = currentDate.getDay();
    
    // Create the last 7 days in correct order
    const last7Days = [];
    for (let i = 6; i >= 0; i--) {
        // Calculate the day index by going backwards from today
        let dayIndex = (todayIndex - i + 7) % 7; // Ensure positive index
        
        const dayName = standardDaysOfWeek[dayIndex];
        
        // Calculate the date for display in tooltip
        const date = new Date(currentDate);
        date.setDate(currentDate.getDate() - i);
        const fullDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        last7Days.push({
            dayName: dayName,
            fullDate: fullDate,
            isToday: i === 0 // Mark today's entry
        });
    }
    
    // Now display each day with the proper labels and improved styling
    for (const dayInfo of last7Days) {
        const dayMoodData = dailyMoods[dayInfo.dayName];
        const dayMoods = dayMoodData ? dayMoodData.moods : [];
        
        let dayMood = "No entries";
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
            moodColor = moodColors[dayMood.toLowerCase()] || "#607D8B";
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
                <div class="day-mood-count">${dayMoods.length > 0 ? `${dayMoods.length} entries` : ''}</div>
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

