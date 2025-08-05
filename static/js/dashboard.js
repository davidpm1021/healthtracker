/**
 * Health Tracker Dashboard JavaScript
 * Alpine.js components and utilities for the 7-inch touchscreen interface
 */

// Main dashboard data component
function dashboardData() {
    return {
        // Current active tab
        activeTab: 'today',
        
        // Modal state
        showModal: false,
        modalTitle: '',
        modalType: '',
        
        // Date information
        todayDate: '',
        weekRange: '',
        monthName: '',
        deviceInfo: '',
        
        // Initialize component
        init() {
            this.updateDateInfo();
            this.updateDeviceInfo();
            this.setupHtmxEvents();
            
            // Update date info every minute
            setInterval(() => {
                this.updateDateInfo();
            }, 60000);
            
            console.log('Dashboard initialized');
        },
        
        // Switch between tabs
        switchTab(tabName) {
            this.activeTab = tabName;
            
            // Store current tab in localStorage for persistence
            localStorage.setItem('healthTracker_activeTab', tabName);
            
            // Log tab switch for analytics
            console.log(`Switched to tab: ${tabName}`);
            
            // Trigger HTMX refresh for the new tab if needed
            this.refreshTabContent(tabName);
        },
        
        // Update date information
        updateDateInfo() {
            const now = new Date();
            
            // Today's date
            this.todayDate = now.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
            
            // Week range (Monday to Sunday)
            const monday = new Date(now);
            const dayOfWeek = now.getDay();
            const diff = now.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            monday.setDate(diff);
            
            const sunday = new Date(monday);
            sunday.setDate(monday.getDate() + 6);
            
            this.weekRange = `${monday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${sunday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
            
            // Month name
            this.monthName = now.toLocaleDateString('en-US', {
                month: 'long',
                year: 'numeric'
            });
        },
        
        // Update device information
        updateDeviceInfo() {
            const screenWidth = window.screen.width;
            const screenHeight = window.screen.height;
            const pixelRatio = window.devicePixelRatio || 1;
            
            this.deviceInfo = `${screenWidth}×${screenHeight} (${pixelRatio}x)`;
        },
        
        // Show manual entry modal
        showManualEntry(type) {
            this.modalType = type;
            
            const titles = {
                'hrv': 'Enter HRV Reading',
                'mood': 'Rate Your Mood',
                'energy': 'Rate Your Energy',
                'notes': 'Add Notes'
            };
            
            this.modalTitle = titles[type] || 'Manual Entry';
            this.showModal = true;
            
            // Load modal content via HTMX
            const modalContent = document.getElementById('modal-form-content');
            if (modalContent) {
                htmx.ajax('GET', `/api/ui/manual-entry-form/${type}`, {
                    target: '#modal-form-content',
                    swap: 'innerHTML'
                });
            }
            
            console.log(`Opening manual entry modal: ${type}`);
        },
        
        // Close modal
        closeModal() {
            this.showModal = false;
            this.modalType = '';
            this.modalTitle = '';
            
            // Clear modal content
            const modalContent = document.getElementById('modal-form-content');
            if (modalContent) {
                modalContent.innerHTML = '';
            }
        },
        
        // Refresh tab content
        refreshTabContent(tabName) {
            const contentMap = {
                'today': '#today-metrics',
                'week': '#week-charts',
                'month': '#month-charts',
                'goals': '#goals-content'
            };
            
            const selector = contentMap[tabName];
            if (selector) {
                const element = document.querySelector(selector);
                if (element && element.hasAttribute('hx-get')) {
                    htmx.trigger(element, 'load');
                }
            }
        },
        
        // Setup HTMX event listeners
        setupHtmxEvents() {
            // Listen for HTMX request errors
            document.addEventListener('htmx:responseError', (event) => {
                console.error('HTMX request failed:', event.detail);
                this.showErrorToast('Failed to load data. Please check your connection.');
            });
            
            // Listen for successful HTMX requests
            document.addEventListener('htmx:afterSwap', (event) => {
                console.log('HTMX content updated:', event.detail.target.id);
                
                // Re-initialize any charts that were loaded
                this.initializeCharts();
            });
            
            // Listen for HTMX before request
            document.addEventListener('htmx:beforeRequest', (event) => {
                console.log('HTMX request starting:', event.detail.xhr.responseURL);
            });
        },
        
        // Initialize charts after content load
        initializeCharts() {
            // This will be called after HTMX loads chart content
            // Chart.js initialization will happen in the loaded content
            console.log('Initializing charts');
        },
        
        // Show error toast
        showErrorToast(message) {
            window.dispatchEvent(new CustomEvent('show-error', {
                detail: { message }
            }));
        },
        
        // Show success toast
        showSuccessToast(message) {
            window.dispatchEvent(new CustomEvent('show-success', {
                detail: { message }
            }));
        }
    };
}

// Sync status component
function syncStatus() {
    return {
        isOnline: navigator.onLine,
        isSyncing: false,
        lastSync: null,
        syncText: 'Checking...',
        
        init() {
            this.updateSyncStatus();
            this.setupOnlineListeners();
            
            // Check sync status every 30 seconds
            setInterval(() => {
                this.checkSyncStatus();
            }, 30000);
        },
        
        updateSyncStatus() {
            if (this.isOnline) {
                if (this.isSyncing) {
                    this.syncText = 'Syncing...';
                } else if (this.lastSync) {
                    const timeDiff = Math.floor((Date.now() - this.lastSync) / 1000 / 60);
                    if (timeDiff < 1) {
                        this.syncText = 'Just synced';
                    } else if (timeDiff < 60) {
                        this.syncText = `${timeDiff}m ago`;
                    } else {
                        const hours = Math.floor(timeDiff / 60);
                        this.syncText = `${hours}h ago`;
                    }
                } else {
                    this.syncText = 'Never synced';
                }
            } else {
                this.syncText = 'Offline';
            }
        },
        
        setupOnlineListeners() {
            window.addEventListener('online', () => {
                this.isOnline = true;
                this.updateSyncStatus();
                console.log('Connection restored');
            });
            
            window.addEventListener('offline', () => {
                this.isOnline = false;
                this.isSyncing = false;
                this.updateSyncStatus();
                console.log('Connection lost');
            });
        },
        
        async checkSyncStatus() {
            if (!this.isOnline) return;
            
            try {
                this.isSyncing = true;
                this.updateSyncStatus();
                
                // Check API health
                const response = await fetch('/api/health', {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (response.ok) {
                    this.lastSync = Date.now();
                    localStorage.setItem('healthTracker_lastSync', this.lastSync.toString());
                } else {
                    console.warn('API health check failed:', response.status);
                }
            } catch (error) {
                console.error('Sync status check failed:', error);
            } finally {
                this.isSyncing = false;
                this.updateSyncStatus();
            }
        }
    };
}

// Utility functions
const HealthTrackerUtils = {
    // Format numbers for display
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined) return '--';
        return Number(value).toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },
    
    // Format dates
    formatDate(dateString, options = {}) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            ...options
        });
    },
    
    // Format time
    formatTime(dateString) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit'
        });
    },
    
    // Get trend arrow and class
    getTrendInfo(slope) {
        if (!slope || Math.abs(slope) < 0.01) {
            return { arrow: '→', class: 'trend-flat', text: 'stable' };
        } else if (slope > 0) {
            return { arrow: '↗', class: 'trend-up', text: 'increasing' };
        } else {
            return { arrow: '↘', class: 'trend-down', text: 'decreasing' };
        }
    },
    
    // Vibrate for touch feedback (if supported)
    hapticFeedback(type = 'light') {
        if ('vibrate' in navigator) {
            const patterns = {
                light: [10],
                medium: [20],
                heavy: [30]
            };
            navigator.vibrate(patterns[type] || patterns.light);
        }
    },
    
    // Debounce function for performance
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle function for performance
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Touch gesture handling
const TouchHandler = {
    startX: 0,
    startY: 0,
    
    init() {
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
    },
    
    handleTouchStart(e) {
        this.startX = e.touches[0].clientX;
        this.startY = e.touches[0].clientY;
    },
    
    handleTouchMove(e) {
        // Add any gesture logic here if needed
    },
    
    handleTouchEnd(e) {
        if (!this.startX || !this.startY) return;
        
        const endX = e.changedTouches[0].clientX;
        const endY = e.changedTouches[0].clientY;
        
        const diffX = this.startX - endX;
        const diffY = this.startY - endY;
        
        // Detect swipe gestures
        if (Math.abs(diffX) > Math.abs(diffY)) {
            // Horizontal swipe
            if (Math.abs(diffX) > 50) { // Minimum swipe distance
                if (diffX > 0) {
                    // Swipe left - next tab
                    this.switchToNextTab();
                } else {
                    // Swipe right - previous tab
                    this.switchToPrevTab();
                }
            }
        }
        
        this.startX = 0;
        this.startY = 0;
    },
    
    switchToNextTab() {
        const tabs = ['today', 'week', 'month', 'goals'];
        const currentApp = Alpine.raw(document.querySelector('#app').__x.$data);
        const currentIndex = tabs.indexOf(currentApp.activeTab);
        const nextIndex = (currentIndex + 1) % tabs.length;
        currentApp.switchTab(tabs[nextIndex]);
        HealthTrackerUtils.hapticFeedback('light');
    },
    
    switchToPrevTab() {
        const tabs = ['today', 'week', 'month', 'goals'];
        const currentApp = Alpine.raw(document.querySelector('#app').__x.$data);
        const currentIndex = tabs.indexOf(currentApp.activeTab);
        const prevIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
        currentApp.switchTab(tabs[prevIndex]);
        HealthTrackerUtils.hapticFeedback('light');
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Health Tracker Dashboard loading...');
    
    // Initialize touch handling
    TouchHandler.init();
    
    // Restore last active tab
    const savedTab = localStorage.getItem('healthTracker_activeTab');
    if (savedTab) {
        // Wait for Alpine to initialize, then set the tab
        setTimeout(() => {
            const appData = document.querySelector('#app').__x.$data;
            if (appData) {
                appData.activeTab = savedTab;
            }
        }, 100);
    }
    
    // Add global error handler
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        // Could show error toast here
    });
    
    // Add performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const perfData = performance.getEntriesByType('navigation')[0];
                console.log(`Page load time: ${Math.round(perfData.loadEventEnd - perfData.fetchStart)}ms`);
            }, 0);
        });
    }
    
    console.log('Health Tracker Dashboard ready');
});

// Global functions for Today view component

// Show manual entry modal (referenced by today-view.html)
window.showManualEntry = function(metricType) {
    const appData = document.querySelector('#app').__x.$data;
    if (appData && appData.showManualEntry) {
        appData.showManualEntry(metricType);
    } else {
        console.warn(`showManualEntry not available for ${metricType}`);
    }
};

// Alpine.js store initialization for Today view  
document.addEventListener('alpine:init', () => {
    // Today stats store (referenced by today-view.html)
    Alpine.store('todayStats', {
        totalMetrics: 0,
        completedGoals: 0,
        streakDays: 0,
        healthScore: '--',
        
        async update() {
            try {
                const response = await fetch('/api/ui/today/stats');
                if (response.ok) {
                    const stats = await response.json();
                    Object.assign(this, stats);
                }
            } catch (error) {
                console.error('Failed to update today stats:', error);
            }
        }
    });
    
    // Manual entry status store (referenced by today-view.html)
    Alpine.store('manualEntryStatus', {
        hrv: 'Not entered today',
        mood: 'Not entered today', 
        energy: 'Not entered today',
        notes: 'No notes today',
        
        async update() {
            try {
                const response = await fetch('/api/ui/today/manual-status');
                if (response.ok) {
                    const status = await response.json();
                    Object.assign(this, status);
                }
            } catch (error) {
                console.error('Failed to update manual entry status:', error);
            }
        }
    });
    
    // Initialize periodic updates
    setTimeout(() => {
        Alpine.store('todayStats').update();
        Alpine.store('manualEntryStatus').update();
        
        // Update every 5 minutes
        setInterval(() => {
            Alpine.store('todayStats').update();
            Alpine.store('manualEntryStatus').update();
        }, 300000);
    }, 1000);
});

// Export utilities for global access
window.HealthTrackerUtils = HealthTrackerUtils;

// Sync banner component
function syncBanner() {
    return {
        syncStatusClass: 'online',
        syncIcon: '🟢',
        syncMessage: 'Connected',
        lastSyncTime: '',
        isRefreshing: false,
        
        checkSyncStatus() {
            this.updateSyncStatus();
        },
        
        updateSyncStatus() {
            const now = new Date();
            this.lastSyncTime = now.toLocaleTimeString();
            this.syncStatusClass = 'online';
            this.syncIcon = '🟢';
            this.syncMessage = 'Connected';
        },
        
        refreshData() {
            if (this.isRefreshing) return;
            
            this.isRefreshing = true;
            // Trigger HTMX refresh for today's content
            setTimeout(() => {
                this.isRefreshing = false;
                this.updateSyncStatus();
            }, 1000);
        }
    };
}

// Export Alpine.js components globally
window.dashboardData = dashboardData;
window.syncStatus = syncStatus;
window.syncBanner = syncBanner;