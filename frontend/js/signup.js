document.addEventListener("DOMContentLoaded", function () {
    // Clear any existing data when the signup page loads
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("lastMood");
    localStorage.removeItem("lastFeedback");
    localStorage.removeItem("rewards");
    localStorage.removeItem("dailyStoryCount");
    localStorage.removeItem("weeklyMoods");
    
    const signupForm = document.getElementById("signup-form");
    const passwordInput = document.getElementById("signup-password");
    const togglePassword = document.getElementById("toggleSignupPassword");

    // Toggle password visibility
    togglePassword.addEventListener("click", function () {
        passwordInput.type = passwordInput.type === "password" ? "text" : "password";
        togglePassword.src = passwordInput.type === "password" ? "../assets/mdi_hide.png" : "../assets/mdi_show.png";
    });

    // Signup form submission
    signupForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const username = document.getElementById("username").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = passwordInput.value.trim();

        if (!username || !email || !password) {
            alert("❌ Username, email, and password are required!");
            return;
        }

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
                
                // Optionally, we could also automatically log in the user here
                // by using tokenManager.setToken(result.token, username);
                // But for now, redirecting to login page is fine
                
                alert("✅ Signup successful! Please login.");
                window.location.href = "login.html";
            } else {
                alert("❌ " + (result.error || "Signup failed. Please try again."));
            }
        } catch (error) {
            console.error("Signup Error:", error);
            alert("❌ Signup failed. Try again later.");
        }
    });
});
