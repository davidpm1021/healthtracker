/**
 * Navigation Enhancement - Health Tracker
 * Enhanced navigation with goals integration
 */

class Navigation {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupMobileToggle();
        this.setupActiveLinks();
        this.updateNavigationBadges();
        this.setupKeyboardShortcuts();
    }
    
    setupMobileToggle() {
        const toggle = document.getElementById('nav-toggle');
        const menu = document.querySelector('.nav-menu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', () => {
                menu.classList.toggle('active');
                toggle.classList.toggle('active');
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!toggle.contains(e.target) && !menu.contains(e.target)) {
                    menu.classList.remove('active');
                    toggle.classList.remove('active');
                }
            });
        }
    }
    
    setupActiveLinks() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage || 
                (currentPage === '' && href === 'index.html') ||
                (currentPage === 'dashboard-enhanced.html' && href === 'index.html')) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
    
    async updateNavigationBadges() {
        try {
            // Get goals count for badge
            const response = await fetch('/api/goals?status=active');
            if (response.ok) {
                const goals = await response.json();
                this.updateGoalsBadge(goals.length);
            }
        } catch (error) {
            console.error('Error updating navigation badges:', error);
        }
    }
    
    updateGoalsBadge(count) {
        const goalsLink = document.querySelector('a[href="goals.html"]');
        if (!goalsLink) return;
        
        let badge = goalsLink.querySelector('.nav-badge');
        
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'nav-badge';
                goalsLink.appendChild(badge);
            }
            badge.textContent = count;
        } else if (badge) {
            badge.remove();
        }
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Alt + number keys for navigation
            if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                switch (e.key) {
                    case '1':
                        e.preventDefault();
                        this.navigateTo('index.html');
                        break;
                    case '2':
                        e.preventDefault();
                        this.navigateTo('charts.html');
                        break;
                    case '3':
                        e.preventDefault();
                        this.navigateTo('goals.html');
                        break;
                    case '4':
                        e.preventDefault();
                        this.navigateTo('manual.html');
                        break;
                }
            }
        });
    }
    
    navigateTo(page) {
        if (window.location.pathname.split('/').pop() !== page) {
            window.location.href = page;
        }
    }
    
    // Public method to refresh badges
    refresh() {
        this.updateNavigationBadges();
    }
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.navigation = new Navigation();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Navigation;
}