// S18-E: Shared Auth Utilities
// Token management, refresh logic, and auth guards

const AUTH = {
    // Token keys
    ACCESS_TOKEN_KEY: 'dna_auth_token',
    REFRESH_TOKEN_KEY: 'dna_refresh_token',
    USER_KEY: 'dna_user',
    REMEMBER_ME_KEY: 'dna_remember_me',
    
    // Token refresh buffer (refresh 2 min before expiry)
    REFRESH_BUFFER_MS: 2 * 60 * 1000,
    
    /**
     * Get access token
     */
    getAccessToken() {
        return sessionStorage.getItem(this.ACCESS_TOKEN_KEY) || localStorage.getItem(this.ACCESS_TOKEN_KEY);
    },
    
    /**
     * Get refresh token
     */
    getRefreshToken() {
        const storage = this.isRememberMe() ? localStorage : sessionStorage;
        return storage.getItem(this.REFRESH_TOKEN_KEY);
    },
    
    /**
     * Check if "remember me" is enabled
     */
    isRememberMe() {
        return localStorage.getItem(this.REMEMBER_ME_KEY) === 'true';
    },
    
    /**
     * Store tokens after login
     */
    setTokens(accessToken, refreshToken, rememberMe = false) {
        // Store access token
        if (rememberMe) {
            localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
            localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
            localStorage.setItem(this.REMEMBER_ME_KEY, 'true');
        } else {
            sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
            sessionStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
            localStorage.removeItem(this.REMEMBER_ME_KEY);
        }
    },
    
    /**
     * Clear all auth data (logout)
     */
    clearTokens() {
        sessionStorage.removeItem(this.ACCESS_TOKEN_KEY);
        sessionStorage.removeItem(this.REFRESH_TOKEN_KEY);
        sessionStorage.removeItem(this.USER_KEY);
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_TOKEN_KEY);
        localStorage.removeItem(this.REMEMBER_ME_KEY);
    },
    
    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.getAccessToken();
    },
    
    /**
     * Get auth headers for API requests
     */
    getAuthHeaders() {
        const token = this.getAccessToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },
    
    /**
     * Refresh access token using refresh token
     */
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        
        if (!refreshToken) {
            console.error('No refresh token available');
            return null;
        }
        
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (!response.ok) {
                throw new Error('Refresh failed');
            }
            
            const data = await response.json();
            
            if (data.access_token) {
                // Update access token (keep same storage type)
                if (this.isRememberMe()) {
                    localStorage.setItem(this.ACCESS_TOKEN_KEY, data.access_token);
                } else {
                    sessionStorage.setItem(this.ACCESS_TOKEN_KEY, data.access_token);
                }
                console.log('Token refreshed successfully');
                return data.access_token;
            }
        } catch (err) {
            console.error('Token refresh failed:', err);
        }
        
        return null;
    },
    
    /**
     * Logout user (invalidate tokens + clear client state)
     */
    async logout(logoutAll = false) {
        const accessToken = this.getAccessToken();
        const refreshToken = this.getRefreshToken();
        
        try {
            // Call logout endpoint to invalidate server-side
            if (accessToken) {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`
                    },
                    body: JSON.stringify({
                        refresh_token: refreshToken,
                        logout_all: logoutAll
                    })
                });
            }
        } catch (err) {
            console.error('Logout API call failed:', err);
            // Continue with client-side logout even if API fails
        }
        
        // Clear client state
        this.clearTokens();
        
        // Redirect to auth screen
        window.location.href = '/app?screen=auth';
    },
    
    /**
     * Auth guard - redirect to login if not authenticated
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            console.log('Auth required, redirecting to login');
            window.location.href = '/app?screen=auth';
            return false;
        }
        return true;
    },
    
    /**
     * Setup automatic token refresh
     */
    setupAutoRefresh() {
        // Refresh token every 10 minutes
        setInterval(async () => {
            if (this.isAuthenticated()) {
                console.log('Auto-refreshing token...');
                await this.refreshAccessToken();
            }
        }, 10 * 60 * 1000); // 10 minutes
    },
    
    /**
     * Fetch wrapper with auth and auto-refresh
     */
    async fetch(url, options = {}) {
        // Add auth headers
        const headers = {
            ...options.headers,
            ...this.getAuthHeaders()
        };
        
        let response = await fetch(url, { ...options, headers });
        
        // If 401, try to refresh token
        if (response.status === 401) {
            console.log('Token expired, attempting refresh...');
            const newToken = await this.refreshAccessToken();
            
            if (newToken) {
                // Retry with new token
                headers['Authorization'] = `Bearer ${newToken}`;
                response = await fetch(url, { ...options, headers });
            } else {
                // Refresh failed, logout
                console.error('Token refresh failed, logging out');
                this.logout();
                return response;
            }
        }
        
        return response;
    }
};

// Auto-setup on load
if (typeof window !== 'undefined') {
    AUTH.setupAutoRefresh();
}
