// AuraQ TokenManager - Enhanced security for auth tokens
class TokenManager {
    constructor() {
        this.tokenKey = "token";
        this.expiryKey = "token_expiry";
        this.usernameKey = "username";
        this.lastMoodKey = "lastMood";
        this.lastFeedbackKey = "lastFeedback";
        this.lastMoodUserKey = "lastMoodUser";
        
        // Check for token expiry immediately
        this.checkTokenExpiry();
    }
    
    // Store the token in sessionStorage with expiry time
    setToken(token, username, expiryInSeconds = 86400) {
        // Calculate expiry time
        const expiryTime = Date.now() + (expiryInSeconds * 1000);
        
        // Store in sessionStorage for better security (cleared when browser closes)
        sessionStorage.setItem(this.tokenKey, token);
        sessionStorage.setItem(this.expiryKey, expiryTime.toString());
        sessionStorage.setItem(this.usernameKey, username);
        
        // Set up expiry checker if on a page that needs authentication
        if (document.getElementById("logout-btn") || document.querySelector(".dashboard")) {
            this.setupExpiryChecker();
        }
        
        console.log("Token stored securely with expiry");
    }
    
    // Get the token if it's valid
    getToken() {
        if (this.isTokenExpired()) {
            this.clearToken();
            return null;
        }
        return sessionStorage.getItem(this.tokenKey);
    }
    
    // Get the username
    getUsername() {
        return sessionStorage.getItem(this.usernameKey) || "User";
    }
    
    // Check if token is expired
    isTokenExpired() {
        const expiryTime = parseInt(sessionStorage.getItem(this.expiryKey) || "0");
        return Date.now() > expiryTime;
    }
    
    // Check token expiry and redirect if expired
    checkTokenExpiry() {
        if (this.isTokenExpired() && sessionStorage.getItem(this.tokenKey)) {
            this.clearToken();
            
            // Only redirect if we're on a protected page
            const currentPage = window.location.pathname;
            if (currentPage.includes("dashboard") || currentPage.includes("profile")) {
                this.showLoginExpired();
            }
        }
    }
    
    // Clear the token and related auth data
    clearToken() {
        sessionStorage.removeItem(this.tokenKey);
        sessionStorage.removeItem(this.expiryKey);
        sessionStorage.removeItem(this.usernameKey);
        sessionStorage.removeItem(this.lastMoodKey);
        sessionStorage.removeItem(this.lastFeedbackKey);
        sessionStorage.removeItem(this.lastMoodUserKey);
    }
    
    // Set up a periodic check for token expiry
    setupExpiryChecker() {
        // Check token expiry every minute
        setInterval(() => this.checkTokenExpiry(), 60000);
    }
    
    // Show modal when login expires
    showLoginExpired() {
        // Create modal element if it doesn't exist
        if (!document.getElementById("session-expired-modal")) {
            const modal = document.createElement("div");
            modal.id = "session-expired-modal";
            modal.className = "auth-modal";
            modal.innerHTML = `
                <div class="auth-modal-content">
                    <h2>Session Expired</h2>
                    <p>Your login session has expired. Please log in again to continue.</p>
                    <button id="session-expired-login">Log In Again</button>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Add event listener to the button
            document.getElementById("session-expired-login").addEventListener("click", () => {
                window.location.href = "login.html";
            });
        }
        
        // Show the modal
        document.getElementById("session-expired-modal").style.display = "flex";
    }
    
    // Store mood data with user association
    saveMoodData(mood, feedback) {
        const username = this.getUsername();
        sessionStorage.setItem(this.lastMoodKey, mood);
        sessionStorage.setItem(this.lastFeedbackKey, feedback);
        sessionStorage.setItem(this.lastMoodUserKey, username);
    }
    
    // Get mood data if it belongs to current user
    getMoodData() {
        const currentUser = this.getUsername();
        const lastUser = sessionStorage.getItem(this.lastMoodUserKey);
        
        if (currentUser && lastUser === currentUser) {
            return {
                mood: sessionStorage.getItem(this.lastMoodKey),
                feedback: sessionStorage.getItem(this.lastFeedbackKey)
            };
        }
        
        return { mood: null, feedback: null };
    }
}

// Create a global token manager instance
const tokenManager = new TokenManager();

// Add CSS for the session expired modal
document.addEventListener("DOMContentLoaded", function() {
    const style = document.createElement("style");
    style.textContent = `
        .auth-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .auth-modal-content {
            background: #1e222b;
            color: #fff;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            max-width: 400px;
        }
        
        .auth-modal-content h2 {
            margin-top: 0;
        }
        
        .auth-modal-content button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 20px;
            font-size: 16px;
        }
        
        .auth-modal-content button:hover {
            background: #0056b3;
        }
    `;
    document.head.appendChild(style);
    
    // Add global event handlers for API errors
    document.addEventListener("apiError", function(e) {
        if (e.detail && e.detail.status === 401) {
            tokenManager.clearToken();
            tokenManager.showLoginExpired();
        }
    });
});

// Helper function to handle API errors consistently
async function fetchWithAuth(url, options = {}) {
    // Get the current token
    const token = tokenManager.getToken();
    
    // If no token and this is an authenticated request, redirect to login
    if (!token && !url.includes("/auth/")) {
        tokenManager.showLoginExpired();
        throw new Error("Authentication required");
    }
    
    // Add authorization header if token exists
    if (token) {
        options.headers = {
            ...options.headers,
            "Authorization": `Bearer ${token}`
        };
    }
    
    // Log the request for debugging
    console.log(`📡 API Request to: ${url}`, { method: options.method || 'GET' });
    
    try {
        const response = await fetch(url, options);
        
        // Handle authentication errors
        if (response.status === 401) {
            console.log("⚠️ Authentication failed (401)");
            tokenManager.clearToken();
            
            // Dispatch custom event
            const event = new CustomEvent("apiError", { 
                detail: { status: 401, message: "Authentication failed" } 
            });
            document.dispatchEvent(event);
            
            throw new Error("Authentication failed");
        }
        
        return response;
    } catch (error) {
        console.error("🔥 API request failed:", error);
        
        // Dispatch custom event for network errors
        if (!error.message.includes("Authentication")) {
            const event = new CustomEvent("apiError", { 
                detail: { status: 0, message: "Network error" } 
            });
            document.dispatchEvent(event);
        }
        
        throw error;
    }
}

// Initialize common elements
document.addEventListener("DOMContentLoaded", function() {
    const navbarContainer = document.getElementById("navbar");
    const footerContainer = document.getElementById("footer");
    
    // Load navbar if container exists
    if (navbarContainer) {
        fetch('../components/navbar.html')
            .then(response => response.text())
            .then(html => {
                navbarContainer.innerHTML = html;
                
                // Setup logout functionality after navbar loads
                const logoutBtn = document.getElementById("logout-btn");
                if (logoutBtn) {
                    logoutBtn.addEventListener("click", function() {
                        tokenManager.clearToken();
                        window.location.href = "login.html";
                    });
                }
                
                // Update username display after navbar loads
                const usernameElement = document.getElementById("username");
                if (usernameElement) {
                    usernameElement.textContent = tokenManager.getUsername();
                }
                
                // Set active nav item based on current page
                highlightCurrentPage();
            });
    }
    
    // Load footer if container exists
    if (footerContainer) {
        fetch('../components/footer.html')
            .then(response => response.text())
            .then(html => {
                footerContainer.innerHTML = html;
            });
    }
});

// Function to highlight the current page in the navigation
function highlightCurrentPage() {
    const currentPage = window.location.pathname.split('/').pop();
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) {
            link.classList.add('active');
        }
    });
}

// Function to load components dynamically
function loadComponent(id, file) {
    // First check if the element exists
    const element = document.getElementById(id);
    if (!element) {
        console.log(`Element with id '${id}' not found, skipping component load`);
        return;
    }
    
    fetch(file)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch ${file}: ${response.status}`);
            }
            return response.text();
        })
        .then(data => {
            element.innerHTML = data;
            
            if (id === "navbar") {
                // Check authentication state and update UI accordingly
                updateAuthUI();
                
                // Add event listener to the logout button
                const logoutButton = document.querySelector('.signout-btn');
                if (logoutButton) {
                    logoutButton.addEventListener('click', logout);
                }
                
                // Update reward points if available (only for authorized users)
                const rewardPoints = document.getElementById("reward-points");
                if (rewardPoints && localStorage.getItem("token")) {
                    // Using 5 as default to be consistent with dashboard.js
                    const rewards = parseInt(localStorage.getItem("rewards")) || 5;
                    rewardPoints.textContent = rewards;
                }
            }
        })
        .catch(error => console.error(`Error loading ${file}:`, error));
}

// Function to update UI based on authentication state
function updateAuthUI() {
    // Create a persistent flag in localStorage instead of using window object
    // which gets reset between page loads
    const token = localStorage.getItem("token");
    const userActionsContainer = document.getElementById("user-actions-container");
    
    // Get current page name
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split("/").pop() || "index.html"; // Default to index.html if empty
    
    console.log("Current page:", currentPage, "Auth token exists:", !!token);
    
    if (userActionsContainer) {
        // Only show user actions for authenticated users, hide for everyone else
        if (token && currentPage === "dashboard.html") {
            userActionsContainer.style.setProperty("display", "flex", "important");
            console.log("Showing user actions for authenticated user");
        } else {
            userActionsContainer.style.setProperty("display", "none", "important");
            console.log("Hiding user actions container");
        }
    }
    
    // Special handling for dashboard - already managed by early script in HTML
    // Let that handle the authentication redirect
}

// Load Navbar & Footer on all pages
document.addEventListener("DOMContentLoaded", () => {
    loadComponent("navbar", "../components/navbar.html");
    loadComponent("footer", "../components/footer.html");
});

// Logout function
function logout() {
    console.log("Logout initiated. Clearing storage..."); // <-- Add log
    // Clear all authentication data from sessionStorage
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("username");
    sessionStorage.removeItem("token_expiry");
    sessionStorage.removeItem("lastMood");
    sessionStorage.removeItem("lastFeedback");
    sessionStorage.removeItem("lastMoodUser");
    sessionStorage.removeItem("rewards");
    sessionStorage.removeItem("dailyStoryCount");
    sessionStorage.removeItem("dashboardInitialized");
    
    // Also clear any remaining localStorage items for completeness
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("rewards");
    localStorage.removeItem("dailyStoryCount");
    localStorage.removeItem("lastResetDate");
    localStorage.removeItem("weeklyMoods");
    localStorage.removeItem("hasRedirected");

    // Log storage state *after* removal attempts
    console.log("Storage after clearing:", {
        sessionToken: sessionStorage.getItem("token"),
        sessionUsername: sessionStorage.getItem("username"),
        localToken: localStorage.getItem("token"),
        localUsername: localStorage.getItem("username")
    });

    window.location.href = "login.html";
}

// Function to view a file
