document.addEventListener("DOMContentLoaded", function () {
    // Clear any existing authentication tokens when the login page loads
    // This prevents showing user actions when coming back to login page
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("token_expiry");
    sessionStorage.removeItem("username");
    
    // Also clear any saved mood data to prevent showing previous users' data
    sessionStorage.removeItem("lastMood");
    sessionStorage.removeItem("lastFeedback");
    sessionStorage.removeItem("rewards");
    sessionStorage.removeItem("dailyStoryCount");
    sessionStorage.removeItem("weeklyMoods");

    const loginForm = document.getElementById("login-form");
    const passwordInput = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");

    // Toggle password visibility
    togglePassword.addEventListener("click", function () {
        passwordInput.type = passwordInput.type === "password" ? "text" : "password";
        togglePassword.src = passwordInput.type === "password" ? "../assets/mdi_hide.png" : "../assets/mdi_show.png";
    });

    // Login form submission
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const username = document.getElementById("username").value;
        const password = passwordInput.value;

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
                
                // Store token and username in sessionStorage only
                sessionStorage.setItem("token", result.token);
                sessionStorage.setItem("username", username);
                
                // Set token expiry for security
                const expiryTime = new Date();
                expiryTime.setHours(expiryTime.getHours() + 24); // 24 hour expiry to match backend
                sessionStorage.setItem("token_expiry", expiryTime.getTime());
                
                console.log("Login successful, token stored in sessionStorage, redirecting to dashboard");
                alert("✅ Login successful!");
                window.location.href = "dashboard.html"; // Redirect after login
            } else {
                alert("❌ " + (result.error || "Invalid credentials!"));
            }
        } catch (error) {
            console.error("Login Error:", error);
            alert("❌ Login failed. Try again later.");
        }
    });
});
