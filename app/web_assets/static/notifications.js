/**
 * Notification Settings JavaScript
 * Handles loading, saving, and validation of notification preferences
 */

// API endpoints
const API_BASE = '/api/notifications';

// State
let currentPreferences = null;
let isSaving = false;

// DOM Elements
const form = document.getElementById('notification-settings');
const loadingState = document.getElementById('loading-state');
const errorState = document.getElementById('error-state');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');
const toastIcon = document.getElementById('toast-icon');
const navBadge = document.getElementById('nav-badge');

// Initialize
async function init() {
    await loadPreferences();
    await loadUnreadCount();
    setupEventListeners();
}

/**
 * Load notification preferences from API
 */
async function loadPreferences() {
    showLoading();
    
    try {
        const token = getAuthToken();
        const response = await fetch(`${API_BASE}/preferences`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/app?screen=auth';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        currentPreferences = data;
        populateForm(data);
        showForm();
        
    } catch (error) {
        console.error('Failed to load preferences:', error);
        showError();
    }
}

/**
 * Load unread notification count for badge
 */
async function loadUnreadCount() {
    try {
        const token = getAuthToken();
        const response = await fetch(`${API_BASE}?page=1&per_page=1`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateBadge(data.unread_count);
        }
    } catch (error) {
        console.error('Failed to load unread count:', error);
    }
}

/**
 * Update navigation badge with unread count
 */
function updateBadge(count) {
    if (count > 0) {
        navBadge.textContent = count > 99 ? '99+' : count;
        navBadge.classList.remove('hidden');
    } else {
        navBadge.classList.add('hidden');
    }
}

/**
 * Populate form with loaded preferences
 */
function populateForm(data) {
    // Master toggle
    setCheckbox('enabled', data.enabled);
    
    // Opportunity alerts
    const alerts = data.opportunity_alerts || {};
    setCheckbox('favorite_sports_only', alerts.sports?.length > 0 || false);
    setCheckbox('avoid_volatility', false); // Not in current schema, default to false
    setSlider('min_confidence', alerts.min_confidence || 70);
    setSlider('max_per_day', alerts.max_notifications_per_day || 10);
    
    // Quiet hours
    const quietHours = data.quiet_hours || {};
    setTimeInput('quiet_hours_start', quietHours.start || '22:00');
    setTimeInput('quiet_hours_end', quietHours.end || '08:00');
    
    // Other notifications
    const betOutcomes = data.bet_outcomes || {};
    setCheckbox('bet_outcomes', betOutcomes.enabled !== false);
    
    const gameReminders = data.game_reminders || {};
    setCheckbox('game_reminders', gameReminders.enabled || false);
    
    // Update slider value displays
    updateSliderDisplays();
}

/**
 * Set checkbox value
 */
function setCheckbox(id, checked) {
    const el = document.getElementById(id);
    if (el) el.checked = checked;
}

/**
 * Set slider value
 */
function setSlider(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

/**
 * Set time input value
 */
function setTimeInput(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

/**
 * Get checkbox value
 */
function getCheckbox(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

/**
 * Get slider value as number
 */
function getSliderValue(id) {
    const el = document.getElementById(id);
    return el ? parseInt(el.value, 10) : 0;
}

/**
 * Get time input value
 */
function getTimeValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

/**
 * Update slider value displays
 */
function updateSliderDisplays() {
    const minConfidence = getSliderValue('min_confidence');
    document.getElementById('min_confidence_value').textContent = `${minConfidence}%`;
    
    const maxPerDay = getSliderValue('max_per_day');
    document.getElementById('max_per_day_value').textContent = maxPerDay;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Form submission
    form.addEventListener('submit', handleSubmit);
    
    // Slider value updates
    document.getElementById('min_confidence').addEventListener('input', updateSliderDisplays);
    document.getElementById('max_per_day').addEventListener('input', updateSliderDisplays);
    
    // Real-time validation for quiet hours
    document.getElementById('quiet_hours_start').addEventListener('change', validateQuietHours);
    document.getElementById('quiet_hours_end').addEventListener('change', validateQuietHours);
}

/**
 * Validate quiet hours selection
 */
function validateQuietHours() {
    const start = getTimeValue('quiet_hours_start');
    const end = getTimeValue('quiet_hours_end');
    
    if (start && end && start === end) {
        showToast('Start and end times cannot be the same', 'error');
        return false;
    }
    
    return true;
}

/**
 * Handle form submission
 */
async function handleSubmit(e) {
    e.preventDefault();
    
    if (isSaving) return;
    if (!validateQuietHours()) return;
    
    isSaving = true;
    setSaveButtonLoading(true);
    
    const payload = buildPayload();
    
    try {
        const token = getAuthToken();
        const response = await fetch(`${API_BASE}/preferences`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        currentPreferences = data;
        showToast('Settings saved successfully', 'success');
        
    } catch (error) {
        console.error('Failed to save preferences:', error);
        showToast(error.message || 'Failed to save settings', 'error');
    } finally {
        isSaving = false;
        setSaveButtonLoading(false);
    }
}

/**
 * Build API payload from form values
 */
function buildPayload() {
    return {
        enabled: getCheckbox('enabled'),
        opportunity_alerts: {
            enabled: true,
            min_confidence: getSliderValue('min_confidence'),
            max_notifications_per_day: getSliderValue('max_per_day'),
            sports: getCheckbox('favorite_sports_only') ? ['favorites'] : [],
            bet_types: ["moneyline", "spread", "total", "prop"],
            odds_range: {"min": -300, "max": 500},
            cooldown_minutes: 60
        },
        quiet_hours: {
            enabled: true,
            start: getTimeValue('quiet_hours_start'),
            end: getTimeValue('quiet_hours_end')
        },
        bet_outcomes: {
            enabled: getCheckbox('bet_outcomes'),
            wins: true,
            losses: true
        },
        game_reminders: {
            enabled: getCheckbox('game_reminders'),
            before_minutes: 30
        }
    };
}

/**
 * Get authentication token from storage
 */
function getAuthToken() {
    return sessionStorage.getItem('dna_auth_token') || 
           localStorage.getItem('dna_auth_token') || 
           '';
}

/**
 * Show loading state
 */
function showLoading() {
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    form.classList.add('hidden');
}

/**
 * Show error state
 */
function showError() {
    loadingState.classList.add('hidden');
    errorState.classList.remove('hidden');
    form.classList.add('hidden');
}

/**
 * Show form
 */
function showForm() {
    loadingState.classList.add('hidden');
    errorState.classList.add('hidden');
    form.classList.remove('hidden');
}

/**
 * Set save button loading state
 */
function setSaveButtonLoading(loading) {
    const btn = document.getElementById('save-btn');
    if (loading) {
        btn.disabled = true;
        btn.innerHTML = `
            <div class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span>Saving...</span>
        `;
    } else {
        btn.disabled = false;
        btn.innerHTML = `
            <iconify-icon icon="lucide:save" class="text-lg"></iconify-icon>
            <span>Save Changes</span>
        `;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    toastMessage.textContent = message;
    
    if (type === 'error') {
        toastIcon.setAttribute('icon', 'lucide:alert-circle');
        toast.classList.add('toast-error');
        toast.classList.remove('toast-success');
    } else {
        toastIcon.setAttribute('icon', 'lucide:check-circle');
        toast.classList.add('toast-success');
        toast.classList.remove('toast-error');
    }
    
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);

// Expose functions for testing
window.notifications = {
    loadPreferences,
    savePreferences: handleSubmit,
    showToast,
    updateBadge
};
