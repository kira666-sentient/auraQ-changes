document.addEventListener("DOMContentLoaded", function () {
    // Check if we have a valid remembered token first
    // If we have one, redirect to dashboard instead of clearing tokens
    if (tokenManager.migrateRememberedToken()) {
        console.log("Valid remembered token found, redirecting to dashboard");
        window.location.href = "dashboard.html";
        return;
    }
    
    // Only clear tokens if we don't have a valid remembered token
    console.log("No valid remembered token, clearing session storage");
    // Clear any existing authentication tokens when the login page loads
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("token_expiry");
    sessionStorage.removeItem("username");
    
    // Also clear any saved mood data to prevent showing previous users' data
    sessionStorage.removeItem("lastMood");
    sessionStorage.removeItem("lastFeedback");
    sessionStorage.removeItem("rewards");
    sessionStorage.removeItem("dailyStoryCount");
    sessionStorage.removeItem("weeklyMoods");

    // Explicitly hide all error/success messages on page load
    document.querySelectorAll(".form-error, .form-success").forEach(element => {
        element.classList.remove("is-active");
        element.style.display = "none";
    });

    const loginForm = document.getElementById("login-form");
    const passwordInput = document.getElementById("password");
    const usernameInput = document.getElementById("username");
    const togglePassword = document.getElementById("togglePassword");
    const submitButton = document.querySelector(".loginpg-btn");
    
    // Get error elements
    const usernameError = document.getElementById("username-error");
    const passwordError = document.getElementById("password-error");
    const loginError = document.getElementById("login-error");
    const loginSuccess = document.getElementById("login-success");

    // Function to show error
    function showError(element, message) {
        element.textContent = message;
        element.style.display = "block";
        element.classList.add("is-active");
        setTimeout(() => {
            element.classList.remove("is-active");
            element.style.display = "none";
        }, 5000); // Hide after 5 seconds
    }

    // Function to show success
    function showSuccess(element, message) {
        element.textContent = message;
        element.style.display = "block";
        element.classList.add("is-active");
    }

    // Function to set button loading state
    function setButtonLoading(isLoading) {
        if (isLoading) {
            submitButton.classList.add("loading");
            submitButton.disabled = true;
        } else {
            submitButton.classList.remove("loading");
            submitButton.disabled = false;
        }
    }

    // Toggle password visibility
    togglePassword.addEventListener("click", function () {
        passwordInput.type = passwordInput.type === "password" ? "text" : "password";
        togglePassword.src = passwordInput.type === "password" ? "../assets/mdi_hide.png" : "../assets/mdi_show.png";
        // Add subtle opacity change instead of transform to avoid position shifting
        togglePassword.style.opacity = "1";
        setTimeout(() => {
            togglePassword.style.opacity = "0.8";
        }, 200);
    });
    
    // Real-time validation for username
    usernameInput.addEventListener("input", function() {
        const username = this.value.trim();
        
        if (!username) {
            this.classList.remove("success");
            this.classList.add("input-error");
            usernameError.textContent = "Username is required";
            usernameError.style.display = "block";
            usernameError.classList.add("is-active");
        } else if (username.length < 3) {
            this.classList.remove("success");
            this.classList.add("input-error");
            usernameError.textContent = "Username must be at least 3 characters";
            usernameError.style.display = "block";
            usernameError.classList.add("is-active");
        } else {
            this.classList.remove("input-error");
            this.classList.add("success");
            usernameError.classList.remove("is-active");
            usernameError.style.display = "none";
        }
    });
    
    // Real-time validation for password
    passwordInput.addEventListener("input", function() {
        const password = this.value.trim();
        
        if (!password) {
            this.classList.remove("success");
            this.classList.add("input-error");
            passwordError.textContent = "Password is required";
            passwordError.style.display = "block";
            passwordError.classList.add("is-active");
        } else if (password.length < 8) {
            this.classList.remove("success");
            this.classList.add("input-error");
            passwordError.textContent = "Password must be at least 8 characters";
            passwordError.style.display = "block";
            passwordError.classList.add("is-active");
        } else {
            this.classList.remove("input-error");
            this.classList.add("success");
            passwordError.classList.remove("is-active");
            passwordError.style.display = "none";
        }
    });

    // Login form submission
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        
        // Reset previous errors
        usernameError.classList.remove("is-active");
        passwordError.classList.remove("is-active");
        loginError.classList.remove("is-active");
        loginSuccess.classList.remove("is-active");
        
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();
        
        // Validate inputs
        let hasError = false;
        
        if (!username) {
            showError(usernameError, "Please enter your username");
            usernameInput.classList.add("input-error");
            hasError = true;
        } else {
            usernameInput.classList.remove("input-error");
        }
        
        if (!password) {
            showError(passwordError, "Please enter your password");
            passwordInput.classList.add("input-error");
            hasError = true;
        } else {
            passwordInput.classList.remove("input-error");
        }
        
        if (hasError) return;

        // Start loading
        setButtonLoading(true);

        try {
            // Use the config system for the API endpoint
            const response = await fetch(config.getUrl('login'), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            const result = await response.json();

            if (response.ok) {
                // Clear any old data again to ensure we don't show previous users' data
                sessionStorage.removeItem("lastMood");
                sessionStorage.removeItem("lastFeedback");
                sessionStorage.removeItem("rewards");
                sessionStorage.removeItem("dailyStoryCount");
                sessionStorage.removeItem("weeklyMoods");
                
                // Check if remember me is checked
                const rememberMe = document.getElementById("remember-me").checked;
                
                // Use TokenManager to set the token with remember me option
                tokenManager.setToken(result.token, username, rememberMe);
                
                // Show success message
                showSuccess(loginSuccess, "Login successful! Redirecting...");
                
                console.log("Login successful, token stored in sessionStorage, redirecting to dashboard");
                
                // Redirect after short delay to show success message
                setTimeout(() => {
                    window.location.href = "dashboard.html"; // Redirect after login
                }, 1500);
            } else {
                // Stop loading
                setButtonLoading(false);
                
                // Show error message from the server or a default message
                showError(loginError, result.error || "Invalid username or password");
                
                // Add shake animation to form for invalid credentials
                loginForm.classList.add("shake");
                setTimeout(() => {
                    loginForm.classList.remove("shake");
                }, 500);
            }
        } catch (error) {
            // Stop loading
            setButtonLoading(false);
            
            console.error("Login Error:", error);
            showError(loginError, "Login failed. Please check your connection and try again.");
        }
    });
    
    // Add shake animation for invalid login
    const style = document.createElement("style");
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .shake {
            animation: shake 0.5s;
        }
        .success {
            border-color: var(--success-color) !important;
            box-shadow: 0 0 0 1px rgba(76, 175, 80, 0.2) !important;
        }
    `;
    document.head.appendChild(style);
});
