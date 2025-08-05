/**
 * Goal Details View - Health Tracker
 * Detailed view and management for individual goals
 */

class GoalDetailsManager {
    constructor(goalId) {
        this.goalId = goalId;
        this.goal = null;
        this.streak = null;
        this.progress = null;
        this.achievements = [];
        this.apiBase = '/api/goals';
        this.progressBase = '/api/progress';
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadGoalData();
        this.renderGoalDetails();
    }
    
    setupEventListeners() {
        // Back button
        const backBtn = document.getElementById('back-to-goals');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                window.location.href = 'goals.html';
            });
        }
        
        // Edit goal button
        const editBtn = document.getElementById('edit-goal-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.editGoal());
        }
        
        // Delete goal button
        const deleteBtn = document.getElementById('delete-goal-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteGoal());
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-details-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
        
        // Manual achievement button
        const manualBtn = document.getElementById('manual-achievement-btn');
        if (manualBtn) {
            manualBtn.addEventListener('click', () => this.showManualAchievementModal());
        }
        
        // Period selector
        const periodSelect = document.getElementById('period-select');
        if (periodSelect) {
            periodSelect.addEventListener('change', (e) => this.changePeriod(e.target.value));
        }
    }
    
    async loadGoalData() {
        try {
            // Load goal details
            const goalResponse = await fetch(`${this.apiBase}/${this.goalId}`);
            if (!goalResponse.ok) {
                throw new Error('Goal not found');
            }
            this.goal = await goalResponse.json();
            
            // Load current progress
            const progressResponse = await fetch(`${this.progressBase}/goal/${this.goalId}/current`);
            if (progressResponse.ok) {
                const progressData = await progressResponse.json();
                this.progress = progressData.progress;
            }
            
            // Load streak data
            const streakResponse = await fetch(`${this.apiBase}/${this.goalId}/streak`);
            if (streakResponse.ok) {
                this.streak = await streakResponse.json();
            }
            
            // Load recent achievements
            await this.loadAchievements();
            
        } catch (error) {
            console.error('Error loading goal data:', error);
            this.showError('Failed to load goal details');
        }
    }
    
    async loadAchievements(limit = 30) {
        try {
            const response = await fetch(`${this.progressBase}/achievements/${this.goalId}?limit=${limit}`);
            if (response.ok) {
                this.achievements = await response.json();
            }
        } catch (error) {
            console.error('Error loading achievements:', error);
        }
    }
    
    renderGoalDetails() {
        if (!this.goal) {
            this.renderError();
            return;
        }
        
        this.renderGoalHeader();
        this.renderProgressSection();
        this.renderStreakSection();
        this.renderAchievementsSection();
        this.renderStatsSection();
    }
    
    renderGoalHeader() {
        const header = document.getElementById('goal-header');
        if (!header) return;
        
        const goalType = this.getGoalTypeInfo(this.goal.goal_type);
        
        header.innerHTML = `
            <div class="goal-icon-large">${goalType.icon}</div>
            <div class="goal-info">
                <h1 class="goal-name">${goalType.name}</h1>
                <div class="goal-meta">
                    <span class="goal-target">${this.formatValue(this.goal.target_value, goalType.unit)} ${goalType.unit}</span>
                    <span class="goal-frequency">${this.goal.frequency}</span>
                    <span class="goal-status status-${this.goal.status}">${this.goal.status}</span>
                </div>
                ${this.goal.description ? `<p class="goal-description">${this.goal.description}</p>` : ''}
            </div>
        `;
    }
    
    renderProgressSection() {
        const section = document.getElementById('progress-section');
        if (!section || !this.progress) return;
        
        const goalType = this.getGoalTypeInfo(this.goal.goal_type);
        const progressPercentage = Math.min(this.progress.progress_percentage, 100);
        
        section.innerHTML = `
            <h2>Current Progress</h2>
            <div class="progress-card">
                <div class="progress-main">
                    <div class="progress-values">
                        <span class="current-value">${this.formatValue(this.progress.actual_value, goalType.unit)}</span>
                        <span class="target-value">/ ${this.formatValue(this.progress.target_value, goalType.unit)}</span>
                    </div>
                    <div class="progress-bar-large">
                        <div class="progress-fill" style="width: ${progressPercentage}%"></div>
                    </div>
                    <div class="progress-meta">
                        <span class="progress-percentage">${Math.round(progressPercentage)}%</span>
                        <span class="progress-date">as of ${new Date(this.progress.date).toLocaleDateString()}</span>
                    </div>
                </div>
                
                <div class="progress-status">
                    ${this.progress.is_achieved ? 
                        '<div class="achievement-badge achieved">✅ Goal Achieved!</div>' :
                        '<div class="achievement-badge pending">⏳ In Progress</div>'
                    }
                </div>
            </div>
        `;
    }
    
    renderStreakSection() {
        const section = document.getElementById('streak-section');
        if (!section) return;
        
        if (!this.streak || this.streak.current_count === 0) {
            section.innerHTML = `
                <h2>Streak</h2>
                <div class="streak-card no-streak">
                    <div class="streak-icon">🔥</div>
                    <div class="streak-info">
                        <div class="streak-count">No active streak</div>
                        <div class="streak-message">Complete your goal to start a streak!</div>
                    </div>
                </div>
            `;
            return;
        }
        
        const streakDays = this.streak.current_count;
        const bestStreak = this.streak.best_count;
        const isPersonalBest = streakDays === bestStreak && streakDays > 0;
        
        section.innerHTML = `
            <h2>Streak</h2>
            <div class="streak-card ${streakDays >= 7 ? 'good-streak' : 'building-streak'}">
                <div class="streak-icon">🔥</div>
                <div class="streak-info">
                    <div class="streak-count">${streakDays} ${streakDays === 1 ? 'day' : 'days'}</div>
                    <div class="streak-message">
                        ${isPersonalBest ? '🎉 Personal best!' : `Best: ${bestStreak} days`}
                    </div>
                    ${this.streak.freeze_tokens_used > 0 ? 
                        `<div class="streak-tokens">🛡️ ${this.streak.freeze_tokens_used} freeze tokens used</div>` : ''
                    }
                </div>
                
                <div class="streak-actions">
                    <button class="btn btn-small" onclick="goalDetails.viewStreakHistory()">
                        View History
                    </button>
                </div>
            </div>
        `;
    }
    
    renderAchievementsSection() {
        const section = document.getElementById('achievements-section');
        if (!section) return;
        
        section.innerHTML = `
            <div class="section-header">
                <h2>Recent Achievements</h2>
                <button class="btn btn-small btn-primary" id="manual-achievement-btn">
                    ➕ Add Manual
                </button>
            </div>
            
            <div class="achievements-list">
                ${this.achievements.length === 0 ? 
                    '<div class="empty-achievements">No achievements yet. Keep working towards your goal!</div>' :
                    this.achievements.slice(0, 10).map(achievement => this.renderAchievementItem(achievement)).join('')
                }
            </div>
            
            ${this.achievements.length > 10 ? 
                '<button class="btn btn-link load-more-achievements">Load More Achievements</button>' : ''
            }
        `;
        
        // Re-attach manual achievement listener
        const manualBtn = document.getElementById('manual-achievement-btn');
        if (manualBtn) {
            manualBtn.addEventListener('click', () => this.showManualAchievementModal());
        }
    }
    
    renderAchievementItem(achievement) {
        const date = new Date(achievement.achieved_date);
        const goalType = this.getGoalTypeInfo(this.goal.goal_type);
        
        return `
            <div class="achievement-item">
                <div class="achievement-date">
                    <div class="date-day">${date.getDate()}</div>
                    <div class="date-month">${date.toLocaleDateString('en-US', { month: 'short' })}</div>
                </div>
                
                <div class="achievement-details">
                    <div class="achievement-value">
                        ${this.formatValue(achievement.actual_value, goalType.unit)} ${goalType.unit}
                    </div>
                    <div class="achievement-notes">${achievement.notes || 'Goal achieved!'}</div>
                </div>
                
                <div class="achievement-actions">
                    <button class="btn-icon delete-achievement" data-achievement-id="${achievement.id}" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }
    
    renderStatsSection() {
        const section = document.getElementById('stats-section');
        if (!section) return;
        
        // Calculate basic stats
        const totalAchievements = this.achievements.length;
        const recentAchievements = this.achievements.filter(a => {
            const achievedDate = new Date(a.achieved_date);
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            return achievedDate >= thirtyDaysAgo;
        }).length;
        
        const consistencyRate = totalAchievements > 0 ? (recentAchievements / 30 * 100) : 0;
        
        section.innerHTML = `
            <h2>Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${totalAchievements}</div>
                    <div class="stat-label">Total Achievements</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-value">${recentAchievements}</div>
                    <div class="stat-label">Last 30 Days</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-value">${Math.round(consistencyRate)}%</div>
                    <div class="stat-label">Consistency Rate</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-value">${this.streak ? this.streak.best_count : 0}</div>
                    <div class="stat-label">Best Streak</div>
                </div>
            </div>
        `;
    }
    
    renderError() {
        const container = document.getElementById('goal-details-container');
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <h2>Goal Not Found</h2>
                    <p>The requested goal could not be found or has been deleted.</p>
                    <button class="btn btn-primary" onclick="window.location.href='goals.html'">
                        Back to Goals
                    </button>
                </div>
            `;
        }
    }
    
    getGoalTypeInfo(goalType) {
        const goalTypes = {
            'steps': { name: 'Daily Steps', unit: 'steps', icon: '👟' },
            'sleep_duration': { name: 'Sleep Duration', unit: 'hours', icon: '😴' },
            'weight_logging': { name: 'Weight Logging', unit: 'entries', icon: '⚖️' },
            'hrv_entry': { name: 'HRV Entry', unit: 'entries', icon: '❤️' },
            'heart_rate_zone': { name: 'Heart Rate Zone', unit: 'minutes', icon: '💗' }
        };
        
        return goalTypes[goalType] || { name: goalType, unit: 'units', icon: '🎯' };
    }
    
    formatValue(value, unit) {
        if (typeof value !== 'number') return '0';
        
        if (unit === 'steps') {
            return value.toLocaleString();
        } else if (unit === 'hours') {
            return value.toFixed(1);
        } else if (unit === 'minutes') {
            return Math.round(value);
        } else {
            return Math.round(value);
        }
    }
    
    async refreshData() {
        const refreshBtn = document.getElementById('refresh-details-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.textContent = 'Refreshing...';
        }
        
        try {
            await this.loadGoalData();
            this.renderGoalDetails();
            this.showSuccess('Goal details refreshed!');
        } catch (error) {
            this.showError('Failed to refresh data');
        } finally {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.textContent = 'Refresh';
            }
        }
    }
    
    async editGoal() {
        // Redirect to goals page with edit mode
        window.location.href = `goals.html#edit-${this.goalId}`;
    }
    
    async deleteGoal() {
        const goalType = this.getGoalTypeInfo(this.goal.goal_type);
        const confirmed = confirm(`Are you sure you want to delete the "${goalType.name}" goal? This action cannot be undone and will remove all associated achievements and streak data.`);
        
        if (!confirmed) return;
        
        try {
            const response = await fetch(`${this.apiBase}/${this.goalId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete goal');
            }
            
            this.showSuccess('Goal deleted successfully!');
            setTimeout(() => {
                window.location.href = 'goals.html';
            }, 2000);
            
        } catch (error) {
            console.error('Error deleting goal:', error);
            this.showError('Failed to delete goal');
        }
    }
    
    showManualAchievementModal() {
        // Implementation for manual achievement modal
        // This would be similar to the goal creation modal
        console.log('Show manual achievement modal for goal:', this.goalId);
    }
    
    showSuccess(message) {
        // Implementation similar to goals.js notification system
        console.log('Success:', message);
    }
    
    showError(message) {
        // Implementation similar to goals.js notification system
        console.error('Error:', message);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Extract goal ID from URL or hash
    const urlParams = new URLSearchParams(window.location.search);
    const goalId = urlParams.get('id') || window.location.hash.replace('#/goals/', '');
    
    if (goalId && !isNaN(goalId)) {
        window.goalDetails = new GoalDetailsManager(parseInt(goalId));
    } else {
        // Redirect to goals page if no valid ID
        window.location.href = 'goals.html';
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GoalDetailsManager;
}