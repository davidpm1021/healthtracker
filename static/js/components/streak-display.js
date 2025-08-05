/**
 * Streak Display Components - Health Tracker
 * Specialized components for streak visualization and interaction
 */

class StreakDisplay {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            goalId: null,
            showFreezeTokens: true,
            showMilestones: true,
            showHistory: false,
            animated: true,
            compact: false,
            ...options
        };
        
        this.streak = null;
        this.goal = null;
        this.freezeTokens = [];
        this.apiBase = '/api/goals';
        
        this.init();
    }
    
    async init() {
        if (!this.container) {
            console.error('Streak display container not found');
            return;
        }
        
        if (this.options.goalId) {
            await this.loadStreakData();
        }
        
        this.render();
        this.setupEventListeners();
    }
    
    async loadStreakData() {
        try {
            // Load streak data
            const streakResponse = await fetch(`${this.apiBase}/${this.options.goalId}/streak`);
            if (streakResponse.ok) {
                this.streak = await streakResponse.json();
            }
            
            // Load goal data for context
            const goalResponse = await fetch(`${this.apiBase}/${this.options.goalId}`);
            if (goalResponse.ok) {
                this.goal = await goalResponse.json();
            }
            
            // Load freeze tokens if needed
            if (this.options.showFreezeTokens) {
                await this.loadFreezeTokens();
            }
            
        } catch (error) {
            console.error('Error loading streak data:', error);
        }
    }
    
    async loadFreezeTokens() {
        try {
            const response = await fetch(`${this.apiBase}/${this.options.goalId}/freeze-tokens`);
            if (response.ok) {
                this.freezeTokens = await response.json();
            }
        } catch (error) {
            console.error('Error loading freeze tokens:', error);
        }
    }
    
    render() {
        if (!this.streak || this.streak.current_count === 0) {
            this.renderNoStreak();
            return;
        }
        
        if (this.options.compact) {
            this.renderCompactStreak();
        } else {
            this.renderFullStreak();
        }
    }
    
    renderNoStreak() {
        this.container.innerHTML = `
            <div class="streak-display no-streak ${this.options.compact ? 'compact' : ''}">
                <div class="streak-icon-container">
                    <div class="streak-icon inactive">🔥</div>
                </div>
                <div class="streak-content">
                    <div class="streak-count">No Streak</div>
                    <div class="streak-message">Complete your goal to start a streak!</div>
                    ${this.options.showFreezeTokens ? this.renderFreezeTokensSection() : ''}
                </div>
            </div>
        `;
    }
    
    renderCompactStreak() {
        const streakClass = this.getStreakClass();
        const flameIntensity = this.getFlameIntensity();
        
        this.container.innerHTML = `
            <div class="streak-display compact ${streakClass}">
                <div class="streak-icon-container">
                    <div class="streak-icon ${flameIntensity}" data-count="${this.streak.current_count}">
                        🔥
                    </div>
                </div>
                <div class="streak-content">
                    <div class="streak-count">${this.streak.current_count}</div>
                    <div class="streak-label">${this.streak.current_count === 1 ? 'day' : 'days'}</div>
                </div>
            </div>
        `;
    }
    
    renderFullStreak() {
        const streakClass = this.getStreakClass();
        const flameIntensity = this.getFlameIntensity();
        const isPersonalBest = this.streak.current_count === this.streak.best_count && this.streak.current_count > 0;
        const nextMilestone = this.getNextMilestone();
        
        this.container.innerHTML = `
            <div class="streak-display full ${streakClass}">
                <div class="streak-header">
                    <div class="streak-icon-container">
                        <div class="streak-icon ${flameIntensity}" data-count="${this.streak.current_count}">
                            🔥
                        </div>
                        ${this.options.animated ? '<div class="streak-sparkles"></div>' : ''}
                    </div>
                    
                    <div class="streak-main">
                        <div class="streak-count-display">
                            <span class="streak-count">${this.streak.current_count}</span>
                            <span class="streak-unit">${this.streak.current_count === 1 ? 'day' : 'days'}</span>
                        </div>
                        
                        <div class="streak-status">
                            ${isPersonalBest ? 
                                '<div class="personal-best">🎉 Personal Best!</div>' :
                                `<div class="best-streak">Best: ${this.streak.best_count} days</div>`
                            }
                        </div>
                    </div>
                </div>
                
                ${this.options.showMilestones ? this.renderMilestonesSection(nextMilestone) : ''}
                ${this.options.showFreezeTokens ? this.renderFreezeTokensSection() : ''}
                
                <div class="streak-actions">
                    <button class="btn-streak-action" data-action="history">
                        📊 View History
                    </button>
                    <button class="btn-streak-action" data-action="share">
                        📤 Share Streak
                    </button>
                </div>
            </div>
        `;
        
        if (this.options.animated) {
            this.animateStreak();
        }
    }
    
    renderMilestonesSection(nextMilestone) {
        const progress = this.getMilestoneProgress(nextMilestone);
        
        return `
            <div class="streak-milestones">
                <div class="milestone-header">
                    <span class="milestone-label">Next Milestone</span>
                    <span class="milestone-target">${nextMilestone} days</span>
                </div>
                
                <div class="milestone-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">
                        ${nextMilestone - this.streak.current_count} days to go
                    </div>
                </div>
                
                <div class="milestone-achievements">
                    ${this.renderMilestoneAchievements()}
                </div>
            </div>
        `;
    }
    
    renderFreezeTokensSection() {
        const availableTokens = this.freezeTokens.filter(t => t.is_available);
        const usedTokens = this.streak.freeze_tokens_used || 0;
        
        return `
            <div class="freeze-tokens-section">
                <div class="tokens-header">
                    <span class="tokens-label">🛡️ Freeze Tokens</span>
                    <span class="tokens-count">${availableTokens.length} available</span>
                </div>
                
                <div class="tokens-display">
                    ${this.renderTokens(availableTokens, usedTokens)}
                </div>
                
                ${availableTokens.length > 0 ? 
                    '<div class="tokens-help">Use a freeze token to protect your streak if you miss a day</div>' : 
                    '<div class="tokens-help">New freeze tokens are issued monthly</div>'
                }
            </div>
        `;
    }
    
    renderTokens(availableTokens, usedTokens) {
        let tokensHtml = '';
        
        // Show available tokens
        for (let i = 0; i < Math.min(availableTokens.length, 3); i++) {
            const token = availableTokens[i];
            const expiresDate = new Date(token.expires_date);
            tokensHtml += `
                <div class="freeze-token available" data-token-id="${token.id}" title="Expires ${expiresDate.toLocaleDateString()}">
                    🛡️
                </div>
            `;
        }
        
        // Show additional available count
        if (availableTokens.length > 3) {
            tokensHtml += `
                <div class="freeze-token-more">
                    +${availableTokens.length - 3}
                </div>
            `;
        }
        
        // Show used tokens indicator
        if (usedTokens > 0) {
            tokensHtml += `
                <div class="freeze-tokens-used">
                    <span class="used-count">${usedTokens} used this streak</span>
                </div>
            `;
        }
        
        return tokensHtml || '<div class="no-tokens">No freeze tokens available</div>';
    }
    
    renderMilestoneAchievements() {
        const milestones = [7, 14, 30, 50, 100];
        let achievementsHtml = '';
        
        for (const milestone of milestones) {
            const achieved = this.streak.best_count >= milestone;
            const current = this.streak.current_count >= milestone;
            
            achievementsHtml += `
                <div class="milestone-badge ${achieved ? 'achieved' : 'pending'} ${current ? 'current' : ''}">
                    <span class="milestone-number">${milestone}</span>
                    ${achieved ? '✅' : '⚪'}
                </div>
            `;
        }
        
        return achievementsHtml;
    }
    
    getStreakClass() {
        const count = this.streak.current_count;
        if (count >= 100) return 'legendary';
        if (count >= 50) return 'epic';
        if (count >= 30) return 'excellent';
        if (count >= 14) return 'great';
        if (count >= 7) return 'good';
        return 'building';
    }
    
    getFlameIntensity() {
        const count = this.streak.current_count;
        if (count >= 100) return 'legendary';
        if (count >= 50) return 'epic';
        if (count >= 30) return 'hot';
        if (count >= 14) return 'warm';
        if (count >= 7) return 'medium';
        return 'small';
    }
    
    getNextMilestone() {
        const milestones = [7, 14, 30, 50, 100, 200, 365, 500, 1000];
        const current = this.streak.current_count;
        
        for (const milestone of milestones) {
            if (current < milestone) {
                return milestone;
            }
        }
        
        // For very long streaks, next milestone is next 100
        return Math.ceil((current + 1) / 100) * 100;
    }
    
    getMilestoneProgress(nextMilestone) {
        const previous = this.getPreviousMilestone(nextMilestone);
        const current = this.streak.current_count;
        const range = nextMilestone - previous;
        const progress = current - previous;
        
        return Math.max(0, Math.min(100, (progress / range) * 100));
    }
    
    getPreviousMilestone(current) {
        const milestones = [0, 7, 14, 30, 50, 100, 200, 365, 500, 1000];
        
        for (let i = milestones.length - 1; i >= 0; i--) {
            if (milestones[i] < current) {
                return milestones[i];
            }
        }
        
        return 0;
    }
    
    animateStreak() {
        const icon = this.container.querySelector('.streak-icon');
        const sparkles = this.container.querySelector('.streak-sparkles');
        
        if (icon) {
            // Add pulse animation for active streaks
            if (this.streak.current_count >= 7) {
                icon.classList.add('pulse');
            }
            
            // Add celebration animation for milestones
            const milestones = [7, 14, 30, 50, 100];
            if (milestones.includes(this.streak.current_count)) {
                this.celebrateMilestone();
            }
        }
        
        if (sparkles) {
            this.animateSparkles();
        }
    }
    
    animateSparkles() {
        const sparkles = this.container.querySelector('.streak-sparkles');
        if (!sparkles) return;
        
        // Create sparkle particles
        for (let i = 0; i < 6; i++) {
            const sparkle = document.createElement('div');
            sparkle.className = 'sparkle';
            sparkle.textContent = ['✨', '⭐', '💫'][Math.floor(Math.random() * 3)];
            sparkle.style.left = Math.random() * 100 + '%';
            sparkle.style.animationDelay = Math.random() * 2 + 's';
            sparkles.appendChild(sparkle);
        }
        
        // Clean up sparkles after animation
        setTimeout(() => {
            sparkles.innerHTML = '';
        }, 3000);
    }
    
    celebrateMilestone() {
        // Create celebration overlay
        const celebration = document.createElement('div');
        celebration.className = 'milestone-celebration';
        celebration.innerHTML = `
            <div class="celebration-content">
                <div class="celebration-icon">🎉</div>
                <div class="celebration-text">Milestone Reached!</div>
                <div class="celebration-count">${this.streak.current_count} Days</div>
            </div>
        `;
        
        document.body.appendChild(celebration);
        
        // Trigger confetti animation
        this.triggerConfetti();
        
        // Remove celebration after animation
        setTimeout(() => {
            celebration.remove();
        }, 3000);
    }
    
    triggerConfetti() {
        // Simple confetti effect
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.backgroundColor = this.getRandomColor();
            confetti.style.animationDelay = Math.random() * 2 + 's';
            document.body.appendChild(confetti);
            
            setTimeout(() => confetti.remove(), 3000);
        }
    }
    
    getRandomColor() {
        const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b', '#eb4d4b', '#6c5ce7'];
        return colors[Math.floor(Math.random() * colors.length)];
    }
    
    setupEventListeners() {
        // Streak action buttons
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-streak-action')) {
                const action = e.target.dataset.action;
                this.handleStreakAction(action);
            }
        });
        
        // Freeze token interactions
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('freeze-token') && e.target.classList.contains('available')) {
                const tokenId = parseInt(e.target.dataset.tokenId);
                this.handleFreezeTokenClick(tokenId);
            }
        });
        
        // Milestone badge clicks
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.milestone-badge')) {
                const badge = e.target.closest('.milestone-badge');
                this.showMilestoneDetails(badge);
            }
        });
    }
    
    handleStreakAction(action) {
        switch (action) {
            case 'history':
                this.showStreakHistory();
                break;
            case 'share':
                this.shareStreak();
                break;
            default:
                console.log('Unknown streak action:', action);
        }
    }
    
    handleFreezeTokenClick(tokenId) {
        if (confirm('Use this freeze token to protect your streak? This action cannot be undone.')) {
            this.useFreezeToken(tokenId);
        }
    }
    
    async useFreezeToken(tokenId) {
        try {
            const response = await fetch(`${this.apiBase}/${this.options.goalId}/freeze-tokens/${tokenId}/use`, {
                method: 'POST'
            });
            
            if (response.ok) {
                await this.loadStreakData();
                this.render();
                this.showNotification('Freeze token used successfully!', 'success');
            } else {
                throw new Error('Failed to use freeze token');
            }
        } catch (error) {
            console.error('Error using freeze token:', error);
            this.showNotification('Failed to use freeze token', 'error');
        }
    }
    
    showStreakHistory() {
        // Implementation would show a modal or navigate to history page
        console.log('Show streak history for goal:', this.options.goalId);
    }
    
    shareStreak() {
        const streakText = `I'm on a ${this.streak.current_count}-day streak! 🔥`;
        
        if (navigator.share) {
            navigator.share({
                title: 'Health Tracker Streak',
                text: streakText,
                url: window.location.href
            });
        } else {
            // Fallback to clipboard
            navigator.clipboard.writeText(streakText).then(() => {
                this.showNotification('Streak copied to clipboard!', 'success');
            });
        }
    }
    
    showMilestoneDetails(badge) {
        const milestoneNumber = badge.querySelector('.milestone-number').textContent;
        const achieved = badge.classList.contains('achieved');
        
        const message = achieved ? 
            `🎉 You've achieved the ${milestoneNumber}-day milestone!` :
            `Reach ${milestoneNumber} days to unlock this milestone`;
        
        this.showNotification(message, achieved ? 'success' : 'info');
    }
    
    showNotification(message, type = 'info') {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `streak-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    // Public methods for external control
    async refresh() {
        await this.loadStreakData();
        this.render();
    }
    
    setGoal(goalId) {
        this.options.goalId = goalId;
        this.loadStreakData().then(() => this.render());
    }
    
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreakDisplay;
}

// Global registration
window.StreakDisplay = StreakDisplay;