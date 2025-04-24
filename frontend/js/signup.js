document.addEventListener("DOMContentLoaded", function () {
    // Clear any existing data when the signup page loads
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("lastMood");
    localStorage.removeItem("lastFeedback");
    localStorage.removeItem("rewards");
    localStorage.removeItem("dailyStoryCount");
    localStorage.removeItem("weeklyMoods");
    
    // Explicitly hide all error/success messages on page load
    document.querySelectorAll(".form-error, .form-success").forEach(element => {
        element.classList.remove("is-active");
        element.style.display = "none";
    });
    
    const signupForm = document.getElementById("signup-form");
    const usernameInput = document.getElementById("username");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("signup-password");
    const togglePassword = document.getElementById("toggleSignupPassword");
    const submitButton = document.querySelector(".signuppg-btn");
    
    // Get error elements
    const usernameError = document.getElementById("username-error");
    const emailError = document.getElementById("email-error");
    const passwordError = document.getElementById("password-error");
    const signupError = document.getElementById("signup-error");
    const signupSuccess = document.getElementById("signup-success");

    // Function to show error
    function showError(element, message) {
        element.textContent = message;
        element.style.display = "block"; // Explicitly set display to block
        element.classList.add("is-active");
        setTimeout(() => {
            element.classList.remove("is-active");
            element.style.display = "none";
        }, 5000); // Hide after 5 seconds
    }

    // Function to show success
    function showSuccess(element, message) {
        element.textContent = message;
        element.style.display = "block"; // Explicitly set display to block
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
    
    // Function to validate email format
    function isValidEmail(email) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailPattern.test(email);
    }

    // Toggle password visibility with animation
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
    
    // Real-time validation for email
    emailInput.addEventListener("input", function() {
        const email = this.value.trim();
        
        if (!email) {
            this.classList.remove("success");
            this.classList.add("input-error");
            emailError.textContent = "Email is required";
            emailError.style.display = "block";
            emailError.classList.add("is-active");
        } else if (!isValidEmail(email)) {
            this.classList.remove("success");
            this.classList.add("input-error");
            emailError.textContent = "Please enter a valid email address";
            emailError.style.display = "block";
            emailError.classList.add("is-active");
        } else {
            this.classList.remove("input-error");
            this.classList.add("success");
            emailError.classList.remove("is-active");
            emailError.style.display = "none";
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

    // Signup form submission
    signupForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        
        // Reset previous errors/success states visually
        document.querySelectorAll('.form-error, .form-success').forEach(el => {
            el.classList.remove('is-active');
            el.style.display = "none";
        });
        document.querySelectorAll('.input-group input').forEach(el => el.classList.remove('input-error', 'input-success')); // Also reset input borders
        
        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        
        // Validate inputs
        let hasError = false;
        
        if (!username || username.length < 3) {
            showError(usernameError, "Username must be at least 3 characters");
            usernameInput.classList.add("input-error");
            hasError = true;
        } else {
            usernameInput.classList.remove("input-error");
        }
        
        if (!email || !isValidEmail(email)) {
            showError(emailError, "Please enter a valid email address");
            emailInput.classList.add("input-error");
            hasError = true;
        } else {
            emailInput.classList.remove("input-error");
        }
        
        if (!password || password.length < 8) {
            showError(passwordError, "Password must be at least 8 characters");
            passwordInput.classList.add("input-error"); // Keep the red border logic
            hasError = true;
        } else {
            passwordInput.classList.remove("input-error");
        }
        
        if (hasError) return;

        // Start loading state
        setButtonLoading(true);

        try {
            // Use the config system for the API endpoint
            const response = await fetch(config.getUrl('register'), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password }),
            });

            const result = await response.json();

            if (response.ok) {
                // Clear any potential localStorage data again before going to login page
                localStorage.removeItem("lastMood");
                localStorage.removeItem("lastFeedback");
                localStorage.removeItem("rewards");
                localStorage.removeItem("dailyStoryCount");
                localStorage.removeItem("weeklyMoods");
                
                // Show success message with animation
                signupSuccess.classList.add("pulse-success");
                showSuccess(signupSuccess, "Account created successfully! Redirecting to login...");
                
                // Redirect after short delay to show success message
                setTimeout(() => {
                    window.location.href = "login.html";
                }, 2000);
            } else {
                // Stop loading state
                setButtonLoading(false);
                
                // Show error message from the server or a default message
                const errorMessage = result.error || "Unable to create account. Please try again.";
                showError(signupError, errorMessage);
                
                // Add shake animation to form for invalid data
                signupForm.classList.add("shake");
                setTimeout(() => {
                    signupForm.classList.remove("shake");
                }, 500);
            }
        } catch (error) {
            // Stop loading state
            setButtonLoading(false);
            
            console.error("Signup Error:", error);
            showError(signupError, "Signup failed. Please check your connection and try again.");
        }
    });
    
    // Add animations
    const style = document.createElement("style");
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        
        @keyframes pulse-success {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .shake {
            animation: shake 0.5s;
        }
        
        .pulse-success {
            animation: pulse-success 0.5s;
        }
        
        .success {
            border-color: var(--success-color) !important;
            box-shadow: 0 0 0 1px rgba(76, 175, 80, 0.2) !important;
        }
        
        .input-group {
            transition: all var(--transition-medium);
        }
    `;
    document.head.appendChild(style);
});
