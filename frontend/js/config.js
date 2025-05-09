/**
 * AuraQ API Configuration
 * 
 * This file centralizes all API endpoint configuration to make deployment easier.
 * The API_BASE_URL will be determined based on the current environment.
 */

const config = {
    // Dynamically determine API base URL 
    API_BASE_URL: (() => {
        // For local development
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            return "http://127.0.0.1:5000";
        }
        
        // For production
        // Replace this with your actual backend URL after deployment
        return "https://aura-q-backend-9urma8ec3-karan-guptas-projects-17f555cf.vercel.app";
    })(),
    
    // API endpoints
    endpoints: {
        // Auth endpoints
        register: "/auth/register",
        login: "/auth/login",
        
        // User data endpoints
        analyze: "/analyze",
        userHistory: "/user/history",
        userStatistics: "/user/statistics",
        userRewards: "/user/rewards",
        userDailyCount: "/user/daily-count",
        userWeeklyMood: "/user/weekly-mood",
        
        // Health check
        health: "/health"
    },
    
    // Get full URL for an endpoint
    getUrl(endpoint) {
        return this.API_BASE_URL + this.endpoints[endpoint];
    }
};

// Freeze the config to prevent accidental changes
Object.freeze(config);
Object.freeze(config.endpoints);