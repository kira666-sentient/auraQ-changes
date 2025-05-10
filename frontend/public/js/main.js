// AuraQ TokenManager - Enhanced security for auth tokens
class TokenManager {
    constructor() {
        this.tokenKey = "token";
        this.expiryKey = "token_expiry";
        this.usernameKey = "username";
        this.lastMoodKey = "lastMood";
        this.lastFeedbackKey = "lastFeedback";
        this.lastMoodUserKey = "lastMoodUser";
        this.rememberMeKey = "remember_me";
        
        // Check for token expiry immediately
        this.checkTokenExpiry();
        
        // If remember me is enabled, try to retrieve token from localStorage
        this.migrateRememberedToken();
    }
    
    // New method to migrate remembered token from localStorage to sessionStorage
    migrateRememberedToken() {
        // Only proceed if we don't already have a session token
        if (!sessionStorage.getItem(this.tokenKey)) {
            const rememberedToken = localStorage.getItem(this.tokenKey);
            const rememberedUsername = localStorage.getItem(this.usernameKey);
            const rememberedExpiry = localStorage.getItem(this.expiryKey);
            
            // Check if we have a valid remembered token that hasn't expired
            if (rememberedToken && rememberedUsername && rememberedExpiry) {
                const expiryTime = parseInt(rememberedExpiry);
                
                // Only use the token if it's still valid
                if (Date.now() < expiryTime) {
                    console.log("Restoring remembered login session");
                    
                    // Copy values to sessionStorage for active use
                    sessionStorage.setItem(this.tokenKey, rememberedToken);
                    sessionStorage.setItem(this.usernameKey, rememberedUsername);
                    sessionStorage.setItem(this.expiryKey, rememberedExpiry);
                    sessionStorage.setItem(this.rememberMeKey, "true");
                    
                    return true;
                } else {
                    // Token expired, clean up localStorage
                    this.clearRememberedToken();
                }
            }
        }
        return false;
    }
    
    // Store the token in sessionStorage with expiry time
    setToken(token, username, rememberMe = false, expiryInSeconds = 86400) {
        // Calculate expiry time
        const expiryTime = Date.now() + (expiryInSeconds * 1000);
        
        // Store in sessionStorage for better security (cleared when browser closes)
        sessionStorage.setItem(this.tokenKey, token);
        sessionStorage.setItem(this.expiryKey, expiryTime.toString());
        sessionStorage.setItem(this.usernameKey, username);
        sessionStorage.setItem(this.rememberMeKey, rememberMe ? "true" : "false");
        
        // If remember me is checked, also store in localStorage for persistence
        if (rememberMe) {
            localStorage.setItem(this.tokenKey, token);
            localStorage.setItem(this.expiryKey, expiryTime.toString());
            localStorage.setItem(this.usernameKey, username);
        }
        
        // Set up expiry checker if on a page that needs authentication
        if (document.querySelector(".signout-btn") || document.querySelector(".dashboard")) {
            this.setupExpiryChecker();
        }
        
        console.log(`Token stored securely with expiry. Remember me: ${rememberMe}`);
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
    
    // Check if "remember me" is enabled
    isRememberMeEnabled() {
        return sessionStorage.getItem(this.rememberMeKey) === "true";
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
        // Clear from sessionStorage
        sessionStorage.removeItem(this.tokenKey);
        sessionStorage.removeItem(this.expiryKey);
        sessionStorage.removeItem(this.usernameKey);
        sessionStorage.removeItem(this.lastMoodKey);
        sessionStorage.removeItem(this.lastFeedbackKey);
        sessionStorage.removeItem(this.lastMoodUserKey);
        sessionStorage.removeItem(this.rememberMeKey);
        
        // Also clear from localStorage if we were using remember me
        this.clearRememberedToken();
    }
    
    // Clear only the remembered token from localStorage
    clearRememberedToken() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.expiryKey);
        localStorage.removeItem(this.usernameKey);
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
                window.location.href = "/pages_old/login.html"; // MODIFIED: Use direct path to login.html
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
    
    // Determine if we should show error toasts (default to true)
    const showErrorToasts = options.showErrorToasts !== false;
    
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
            
            if (showErrorToasts) {
                apiErrorHandler.showError("Your session has expired. Please log in again.");
            }
            
            throw new Error("Authentication failed");
        }
        
        // Handle other common error codes with toast notifications
        if (!response.ok && showErrorToasts) {
            let errorMessage = "An error occurred";
            
            try {
                // Try to get error message from JSON response
                const errorData = await response.clone().json();
                errorMessage = errorData.error || errorData.message || errorMessage;
            } catch (e) {
                // If not JSON or no error field, use status text
                errorMessage = response.statusText || errorMessage;
            }
            
            apiErrorHandler.handleApiError({ 
                status: response.status, 
                message: errorMessage 
            });
        }
        
        return response;
    } catch (error) {
        console.error("🔥 API request failed:", error);
        
        // Display network error toast for connectivity issues
        if (showErrorToasts && error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            apiErrorHandler.showError("Network error: Please check your internet connection.");
        }
        
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
        fetch('/components/navbar.html')
            .then(response => response.text())
            .then(html => {
                navbarContainer.innerHTML = html;
                
                // Setup logout functionality after navbar loads
                const logoutBtn = document.querySelector('.signout-btn');
                if (logoutBtn) {
                    logoutBtn.addEventListener("click", function() {
                        tokenManager.clearToken();
                        window.location.href = "/pages_old/login.html"; // MODIFIED: Use direct path to login.html
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
        fetch('/components/footer.html')
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
    // Use the tokenManager to check for a valid session token
    const token = tokenManager.getToken();
    const userActionsContainer = document.getElementById("user-actions-container");
    
    // Get current page name
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split("/").pop() || "index.html"; // Default to index.html if empty
    
    console.log("Current page:", currentPage, "Auth token exists:", !!token);
    
    if (userActionsContainer) {
        // Only show user actions for authenticated users on the dashboard page
        if (token && currentPage === "dashboard.html") {
            userActionsContainer.style.display = "flex"; // Remove setProperty and !important
            console.log("Showing user actions for authenticated user");
        } else {
            userActionsContainer.style.display = "none"; // Remove setProperty and !important
            console.log("Hiding user actions container");
        }
    }
    
    // Special handling for dashboard - already managed by early script in HTML
    // Let that handle the authentication redirect
}

// Load Navbar & Footer on all pages
document.addEventListener("DOMContentLoaded", () => {
    loadComponent("navbar", "/components/navbar.html");
    loadComponent("footer", "/components/footer.html");
});

// Logout function
function logout() {
    console.log("Logout initiated. Clearing storage...");
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

    window.location.href = "/pages_old/login.html"; // MODIFIED: Use direct path to login.html
}

// Loading indicator utility functions
const loadingUtils = {
    show: function(message = "Loading...") {
        const overlay = document.getElementById("loading-overlay");
        if (overlay) {
            const textElement = overlay.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
            overlay.classList.add("active");
        } else {
            // If overlay doesn't exist in DOM, create one dynamically
            const newOverlay = document.createElement("div");
            newOverlay.id = "loading-overlay";
            newOverlay.className = "loading-overlay active";
            newOverlay.innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <p class="loading-text">${message}</p>
                </div>
            `;
            document.body.appendChild(newOverlay);
        }
    },
    
    hide: function() {
        const overlay = document.getElementById("loading-overlay");
        if (overlay) {
            overlay.classList.remove("active");
        }
    },
    
    withLoading: async function(promise, message = "Loading...") {
        this.show(message);
        try {
            return await promise;
        } finally {
            this.hide();
        }
    }
};

// API Error Handler utility
const apiErrorHandler = {
    // Store for active error toasts
    toasts: [],
    
    // Create and show an error toast notification
    showError: function(message, type = "error", duration = 5000) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById("toast-container");
        if (!toastContainer) {
            toastContainer = document.createElement("div");
            toastContainer.id = "toast-container";
            toastContainer.style.position = "fixed";
            toastContainer.style.bottom = "20px";
            toastContainer.style.right = "20px";
            toastContainer.style.zIndex = "9999";
            document.body.appendChild(toastContainer);
        }
        
        // Create the toast element
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-message">${message}</span>
                <button class="toast-close">&times;</button>
            </div>
        `;
        
        // Style the toast
        toast.style.backgroundColor = type === "error" ? "#f44336" : "#4CAF50";
        toast.style.color = "white";
        toast.style.padding = "12px 16px";
        toast.style.marginTop = "10px";
        toast.style.borderRadius = "4px";
        toast.style.minWidth = "250px";
        toast.style.boxShadow = "0 2px 5px rgba(0,0,0,0.2)";
        toast.style.animation = "fadeIn 0.5s, fadeOut 0.5s " + (duration / 1000 - 0.5) + "s";
        toast.style.opacity = "0";
        
        // Add close button handler
        toast.querySelector(".toast-close").addEventListener("click", () => {
            this.removeToast(toast);
        });
        
        // Add to DOM
        toastContainer.appendChild(toast);
        
        // Force browser to recalculate styles before animation
        void toast.offsetWidth;
        toast.style.opacity = "1";
        
        // Add to active toasts
        this.toasts.push(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);
        
        return toast;
    },
    
    // Remove a toast from the DOM
    removeToast: function(toast) {
        if (!toast || !toast.parentElement) return;
        
        // Start fade out animation
        toast.style.opacity = "0";
        
        // Remove after animation completes
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
            // Remove from active toasts
            const index = this.toasts.indexOf(toast);
            if (index !== -1) {
                this.toasts.splice(index, 1);
            }
        }, 500);
    },
    
    // Handle common API errors
    handleApiError: function(error) {
        let message = "An error occurred while connecting to the server.";
        
        if (error.status === 401) {
            message = "Your session has expired. Please log in again.";
        } else if (error.status === 403) {
            message = "You don't have permission to access this resource.";
        } else if (error.status === 404) {
            message = "The requested resource was not found.";
        } else if (error.status === 429) {
            message = "Too many requests. Please try again later.";
        } else if (error.status >= 500) {
            message = "Server error. Please try again later.";
        }
        
        if (error.message) {
            message += ` (${error.message})`;
        }
        
        return this.showError(message);
    }
};

// Function to view a file
