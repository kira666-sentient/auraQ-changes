/**
 * AuraQ API Configuration
 * 
 * This file centralizes all API endpoint configuration to make deployment easier.
 * Change the API_BASE_URL to your Vercel deployment URL when deploying.
 */

const config = {
    // For local development
    API_BASE_URL: "http://127.0.0.1:5000",
    
    // For Vercel deployment (uncomment and update when deploying)
    // API_BASE_URL: "https://your-vercel-backend-url.vercel.app",
    
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