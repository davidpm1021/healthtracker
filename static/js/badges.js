/**
 * Badges System - Health Tracker
 * Client-side JavaScript for badge display and management
 */

// Badge display manager
window.BadgeManager = {
    // Initialize badge system
    init: function() {
        console.log('Initializing badge manager...');
        
        // Load badge data on initialization
        this.loadBadgeData();
        
        // Set up periodic refresh (every 5 minutes)
        setInterval(() => this.loadBadgeData(), 5 * 60 * 1000);
        
        // Set up event listeners
        this.setupEventListeners();
    },
    
    // Load badge data from API
    loadBadgeData: async function() {
        try {
            const response = await fetch('/api/badges/ui/display');
            if (!response.ok) throw new Error('Failed to load badge data');
            
            const data = await response.json();
            this.updateBadgeDisplay(data);
            
            // Update navigation badge count if available
            if (window.NavigationBadges) {
                window.NavigationBadges.updateBadgeCounts({
                    badges: data.summary.total_earned
                });
            }
            
        } catch (error) {
            console.error('Error loading badge data:', error);
        }
    },
    
    // Update badge display in UI
    updateBadgeDisplay: function(data) {
        // Update summary stats
        this.updateSummaryStats(data.summary);
        
        // Update earned badges display
        this.updateEarnedBadges(data.earned_by_tier);
        
        // Update recent badges
        this.updateRecentBadges(data.recent_badges);
        
        // Update next badges to earn
        this.updateNextBadges(data.next_to_earn);
        
        // Update category progress
        this.updateCategoryProgress(data.categories);
    },
    
    // Update summary statistics
    updateSummaryStats: function(summary) {
        const elements = {
            'badge-total-earned': summary.total_earned,
            'badge-total-available': summary.total_available,
            'badge-total-points': summary.total_points,
            'badge-completion-percentage': `${summary.completion_percentage}%`
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
        
        // Update progress bar if exists
        const progressBar = document.getElementById('badge-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${summary.completion_percentage}%`;
        }
    },
    
    // Update earned badges display
    updateEarnedBadges: function(earnedByTier) {
        const container = document.getElementById('earned-badges-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Display badges by tier
        const tiers = ['platinum', 'gold', 'silver', 'bronze'];
        
        tiers.forEach(tier => {
            const badges = earnedByTier[tier] || [];
            if (badges.length === 0) return;
            
            const tierSection = document.createElement('div');
            tierSection.className = `badge-tier-section ${tier}-tier`;
            
            const tierHeader = document.createElement('h4');
            tierHeader.className = 'tier-header';
            tierHeader.innerHTML = `<span class="tier-name">${this.capitalize(tier)}</span> <span class="tier-count">(${badges.length})</span>`;
            tierSection.appendChild(tierHeader);
            
            const badgeGrid = document.createElement('div');
            badgeGrid.className = 'badge-grid';
            
            badges.forEach(badge => {
                const badgeElement = this.createBadgeElement(badge);
                badgeGrid.appendChild(badgeElement);
            });
            
            tierSection.appendChild(badgeGrid);
            container.appendChild(tierSection);
        });
    },
    
    // Create individual badge element
    createBadgeElement: function(badge) {
        const div = document.createElement('div');
        div.className = 'badge-item ' + (badge.earned ? 'earned' : 'unearned');
        div.setAttribute('data-badge-id', badge.id);
        
        div.innerHTML = `
            <div class="badge-icon">${badge.icon || '🏆'}</div>
            <div class="badge-name">${badge.name}</div>
            ${badge.earned ? `<div class="badge-earned-date">Earned ${this.formatDate(badge.earned_at)}</div>` : ''}
        `;
        
        // Add click handler for details
        div.addEventListener('click', () => this.showBadgeDetails(badge));
        
        return div;
    },
    
    // Update recent badges
    updateRecentBadges: function(recentBadges) {
        const container = document.getElementById('recent-badges-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (recentBadges.length === 0) {
            container.innerHTML = '<p class="no-badges-message">No badges earned yet. Keep going!</p>';
            return;
        }
        
        recentBadges.forEach(badge => {
            const badgeElement = document.createElement('div');
            badgeElement.className = 'recent-badge-item';
            
            badgeElement.innerHTML = `
                <div class="recent-badge-icon">${badge.icon || '🏆'}</div>
                <div class="recent-badge-info">
                    <div class="recent-badge-name">${badge.name}</div>
                    <div class="recent-badge-date">Earned ${this.formatDate(badge.earned_at)}</div>
                </div>
            `;
            
            container.appendChild(badgeElement);
        });
    },
    
    // Update next badges to earn
    updateNextBadges: function(nextBadges) {
        const container = document.getElementById('next-badges-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        nextBadges.forEach(badge => {
            const badgeElement = document.createElement('div');
            badgeElement.className = 'next-badge-item';
            
            badgeElement.innerHTML = `
                <div class="next-badge-icon">${badge.icon || '🎯'}</div>
                <div class="next-badge-info">
                    <div class="next-badge-name">${badge.name}</div>
                    <div class="next-badge-description">${badge.description}</div>
                    <div class="next-badge-tier ${badge.tier}-tier">${this.capitalize(badge.tier)}</div>
                </div>
            `;
            
            badgeElement.addEventListener('click', () => this.showBadgeDetails(badge));
            container.appendChild(badgeElement);
        });
    },
    
    // Update category progress
    updateCategoryProgress: function(categories) {
        const container = document.getElementById('category-progress-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(categories).forEach(([category, data]) => {
            const percentage = data.total > 0 ? Math.round((data.earned / data.total) * 100) : 0;
            
            const categoryElement = document.createElement('div');
            categoryElement.className = 'category-progress-item';
            
            categoryElement.innerHTML = `
                <div class="category-header">
                    <span class="category-name">${this.capitalize(category)}</span>
                    <span class="category-stats">${data.earned}/${data.total}</span>
                </div>
                <div class="category-progress-bar">
                    <div class="category-progress-fill" style="width: ${percentage}%"></div>
                </div>
            `;
            
            container.appendChild(categoryElement);
        });
    },
    
    // Show badge details modal
    showBadgeDetails: function(badge) {
        const modal = document.getElementById('badge-details-modal');
        if (!modal) {
            console.warn('Badge details modal not found');
            return;
        }
        
        // Update modal content
        document.getElementById('badge-detail-icon').textContent = badge.icon || '🏆';
        document.getElementById('badge-detail-name').textContent = badge.name;
        document.getElementById('badge-detail-description').textContent = badge.description;
        document.getElementById('badge-detail-tier').textContent = this.capitalize(badge.tier);
        document.getElementById('badge-detail-tier').className = `badge-tier ${badge.tier}-tier`;
        
        if (badge.earned) {
            document.getElementById('badge-detail-earned').style.display = 'block';
            document.getElementById('badge-detail-earned-date').textContent = this.formatDate(badge.earned_at);
        } else {
            document.getElementById('badge-detail-earned').style.display = 'none';
        }
        
        // Show modal
        modal.style.display = 'flex';
    },
    
    // Set up event listeners
    setupEventListeners: function() {
        // Close modal when clicking outside
        const modal = document.getElementById('badge-details-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
        
        // Close button
        const closeBtn = document.getElementById('close-badge-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
        
        // Evaluate badges button
        const evaluateBtn = document.getElementById('evaluate-badges-btn');
        if (evaluateBtn) {
            evaluateBtn.addEventListener('click', () => this.evaluateBadges());
        }
    },
    
    // Evaluate badges (check for new earned badges)
    evaluateBadges: async function() {
        try {
            const response = await fetch('/api/badges/evaluate', {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Failed to evaluate badges');
            
            const newBadges = await response.json();
            
            if (newBadges.length > 0) {
                // Show celebration for new badges
                this.celebrateNewBadges(newBadges);
                
                // Reload badge data
                await this.loadBadgeData();
            } else {
                // Show message that no new badges were earned
                this.showNotification('No new badges earned yet. Keep it up!', 'info');
            }
            
        } catch (error) {
            console.error('Error evaluating badges:', error);
            this.showNotification('Failed to evaluate badges', 'error');
        }
    },
    
    // Celebrate new badges earned
    celebrateNewBadges: function(badges) {
        // Simple celebration - could be enhanced with confetti animation
        badges.forEach((badge, index) => {
            setTimeout(() => {
                this.showNotification(
                    `🎉 New badge earned: ${badge.name}!`,
                    'success',
                    5000
                );
            }, index * 1000);
        });
    },
    
    // Show notification
    showNotification: function(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after duration
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    },
    
    // Utility functions
    formatDate: function(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        
        return date.toLocaleDateString();
    },
    
    capitalize: function(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on a page with badge elements
    if (document.getElementById('earned-badges-container') || 
        document.getElementById('badge-total-earned')) {
        window.BadgeManager.init();
    }
});