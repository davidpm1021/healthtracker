/**
 * Streak Components Index - Health Tracker
 * Centralized exports for all streak-related components
 */

// Import all streak components
if (typeof require !== 'undefined') {
    // Node.js environment
    module.exports = {
        StreakDisplay: require('./streak-display'),
        StreakCalendar: require('./streak-calendar'),
        StreakAnalytics: require('./streak-analytics')
    };
} else {
    // Browser environment - components are loaded via script tags
    // This file serves as documentation of available components
    
    /**
     * Available Streak Components:
     * 
     * 1. StreakDisplay - Main streak visualization component
     *    - Shows current streak with flame animation
     *    - Displays freeze tokens and milestones
     *    - Supports compact and full display modes
     *    - Interactive actions (share, history, token usage)
     * 
     * 2. StreakCalendar - Calendar-based streak visualization
     *    - Monthly/multi-month calendar view
     *    - Shows achievement patterns and streaks
     *    - Freeze token usage indicators
     *    - Milestone highlighting
     *    - Interactive tooltips and navigation
     * 
     * 3. StreakAnalytics - Advanced streak analytics and insights
     *    - Performance summaries and trends
     *    - Day-of-week patterns analysis
     *    - Streak predictions and forecasts
     *    - Period-over-period comparisons
     *    - AI-driven insights and recommendations
     */
    
    // Utility function to initialize all components for a goal
    window.initializeStreakComponents = function(goalId, options = {}) {
        const components = {};
        
        // Initialize StreakDisplay
        const displayContainer = document.querySelector(options.displaySelector || '.streak-display-container');
        if (displayContainer) {
            components.display = new StreakDisplay(displayContainer, {
                goalId,
                ...options.display
            });
        }
        
        // Initialize StreakCalendar
        const calendarContainer = document.querySelector(options.calendarSelector || '.streak-calendar-container');
        if (calendarContainer) {
            components.calendar = new StreakCalendar(calendarContainer, {
                goalId,
                ...options.calendar
            });
        }
        
        // Initialize StreakAnalytics
        const analyticsContainer = document.querySelector(options.analyticsSelector || '.streak-analytics-container');
        if (analyticsContainer) {
            components.analytics = new StreakAnalytics(analyticsContainer, {
                goalId,
                ...options.analytics
            });
        }
        
        return components;
    };
    
    // Utility function to refresh all components
    window.refreshStreakComponents = function(components) {
        Object.values(components).forEach(component => {
            if (component && typeof component.refresh === 'function') {
                component.refresh();
            }
        });
    };
    
    // Component factory function
    window.createStreakComponent = function(type, container, options = {}) {
        switch (type.toLowerCase()) {
            case 'display':
                return new StreakDisplay(container, options);
            case 'calendar':
                return new StreakCalendar(container, options);
            case 'analytics':
                return new StreakAnalytics(container, options);
            default:
                throw new Error(`Unknown streak component type: ${type}`);
        }
    };
    
    // Event system for component communication
    window.StreakComponentEvents = {
        // Event types
        STREAK_UPDATED: 'streak:updated',
        GOAL_CHANGED: 'goal:changed',
        ACHIEVEMENT_ADDED: 'achievement:added',
        FREEZE_TOKEN_USED: 'freeze:token:used',
        MILESTONE_REACHED: 'milestone:reached',
        
        // Event dispatcher
        dispatch: function(eventType, data = {}) {
            const event = new CustomEvent(eventType, {
                detail: data,
                bubbles: true
            });
            document.dispatchEvent(event);
        },
        
        // Event listener helper
        listen: function(eventType, callback) {
            document.addEventListener(eventType, callback);
        },
        
        // Remove event listener
        unlisten: function(eventType, callback) {
            document.removeEventListener(eventType, callback);
        }
    };
    
    // Global configuration defaults
    window.StreakComponentDefaults = {
        display: {
            showFreezeTokens: true,
            showMilestones: true,
            animated: true,
            compact: false
        },
        calendar: {
            showMonths: 6,
            showFreezeTokens: true,
            showTooltips: true,
            allowNavigation: true
        },
        analytics: {
            period: 'last_90_days',
            showPatterns: true,
            showPredictions: true,
            showComparisons: true
        }
    };
    
    // Theme customization
    window.StreakComponentThemes = {
        default: {
            primaryColor: '#2563eb',
            successColor: '#10b981',
            warningColor: '#f59e0b',
            errorColor: '#ef4444'
        },
        
        dark: {
            primaryColor: '#3b82f6',
            successColor: '#34d399',
            warningColor: '#fbbf24',
            errorColor: '#f87171'
        },
        
        minimal: {
            primaryColor: '#6b7280',
            successColor: '#6b7280',
            warningColor: '#6b7280',
            errorColor: '#6b7280'
        }
    };
    
    // Performance monitoring
    window.StreakComponentPerformance = {
        startTime: null,
        
        start: function(componentName) {
            this.startTime = performance.now();
            console.log(`Starting ${componentName} initialization...`);
        },
        
        end: function(componentName) {
            if (this.startTime) {
                const duration = performance.now() - this.startTime;
                console.log(`${componentName} initialized in ${duration.toFixed(2)}ms`);
                this.startTime = null;
            }
        }
    };
}

// Component registration for auto-initialization
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize components with data-streak-component attribute
    const autoInitElements = document.querySelectorAll('[data-streak-component]');
    
    autoInitElements.forEach(element => {
        const componentType = element.dataset.streakComponent;
        const goalId = element.dataset.goalId;
        const options = element.dataset.options ? JSON.parse(element.dataset.options) : {};
        
        if (goalId && window[`Streak${componentType.charAt(0).toUpperCase() + componentType.slice(1)}`]) {
            try {
                window.StreakComponentPerformance.start(componentType);
                const ComponentClass = window[`Streak${componentType.charAt(0).toUpperCase() + componentType.slice(1)}`];
                new ComponentClass(element, { goalId, ...options });
                window.StreakComponentPerformance.end(componentType);
            } catch (error) {
                console.error(`Failed to initialize ${componentType} component:`, error);
            }
        }
    });
    
    // Set up global event listeners for component synchronization
    window.StreakComponentEvents.listen(window.StreakComponentEvents.STREAK_UPDATED, function(event) {
        // Refresh all components when streak data is updated
        const allComponents = document.querySelectorAll('[data-streak-component]');
        allComponents.forEach(element => {
            if (element._streakComponent && typeof element._streakComponent.refresh === 'function') {
                element._streakComponent.refresh();
            }
        });
    });
});