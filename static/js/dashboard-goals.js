/**
 * Dashboard Goals Integration - Health Tracker
 * Integrates goals and streaks system with the main dashboard
 */

class DashboardGoals {
    constructor() {
        this.goals = [];
        this.streaks = [];
        this.todayProgress = {};
        this.apiBase = '/api/goals';
        this.progressBase = '/api/progress';
        
        this.init();
    }
    
    async init() {
        await this.loadDashboardData();
        this.renderGoalsWidgets();
        this.setupEventListeners();
        this.startPeriodicUpdates();
    }
    
    async loadDashboardData() {
        try {
            // Load active goals with progress
            const goalsResponse = await fetch(`${this.apiBase}?status=active&include_progress=true`);
            if (goalsResponse.ok) {
                this.goals = await goalsResponse.json();
            }
            
            // Load today's progress dashboard
            const progressResponse = await fetch(`${this.progressBase}/dashboard`);
            if (progressResponse.ok) {
                this.todayProgress = await progressResponse.json();
            }
            
            // Load streak data for each goal
            await this.loadStreakData();
            
        } catch (error) {
            console.error('Error loading dashboard goals data:', error);
        }
    }
    
    async loadStreakData() {
        this.streaks = [];
        
        for (const goal of this.goals) {
            try {
                const streakResponse = await fetch(`${this.apiBase}/${goal.id}/streak`);
                if (streakResponse.ok) {
                    const streak = await streakResponse.json();
                    streak.goalInfo = goal;
                    this.streaks.push(streak);
                }
            } catch (error) {
                console.error(`Error loading streak for goal ${goal.id}:`, error);
            }
        }
    }
    
    renderGoalsWidgets() {
        this.renderGoalsSummaryWidget();
        this.renderStreaksOverview();
        this.renderQuickActions();
        this.renderTodayProgressCards();
        this.updateNavigationBadges();
    }
    
    renderGoalsSummaryWidget() {
        const container = document.getElementById('goals-summary-widget');
        if (!container) return;
        
        const activeGoals = this.goals.filter(g => g.status === 'active');
        const achievedToday = activeGoals.filter(g => g.is_achieved_today).length;
        const totalStreaks = this.streaks.filter(s => s.current_count > 0).length;
        const longestStreak = Math.max(...this.streaks.map(s => s.current_count), 0);
        
        container.innerHTML = `
            <div class="goals-summary-widget">
                <div class="widget-header">
                    <h3 class="widget-title">
                        <span class="widget-icon">🎯</span>
                        Your Goals
                    </h3>
                    <a href="goals.html" class="widget-link">View All</a>
                </div>
                
                <div class="goals-summary-stats">
                    <div class="summary-stat">
                        <div class="stat-value">${achievedToday}</div>
                        <div class="stat-label">Achieved Today</div>
                        <div class="stat-total">of ${activeGoals.length} goals</div>
                    </div>
                    
                    <div class="summary-stat">
                        <div class="stat-value">${totalStreaks}</div>
                        <div class="stat-label">Active Streaks</div>
                        <div class="stat-total">goals on track</div>
                    </div>
                    
                    <div class="summary-stat">
                        <div class="stat-value">${longestStreak}</div>
                        <div class="stat-label">Longest Streak</div>
                        <div class="stat-total">days in a row</div>
                    </div>
                </div>
                
                ${activeGoals.length === 0 ? this.renderEmptyGoalsState() : this.renderGoalsList()}
            </div>
        `;
    }
    
    renderEmptyGoalsState() {
        return `
            <div class="empty-goals-state">
                <div class="empty-icon">🎯</div>
                <div class="empty-title">No Active Goals</div>
                <div class="empty-message">Set your first health goal to start tracking progress</div>
                <button class="btn btn-primary create-goal-btn" data-action="create-goal">
                    Create Your First Goal
                </button>
            </div>
        `;
    }
    
    renderGoalsList() {
        const displayGoals = this.goals.slice(0, 3); // Show top 3 goals
        
        return `
            <div class="dashboard-goals-list">
                ${displayGoals.map(goal => this.renderDashboardGoalCard(goal)).join('')}
                
                ${this.goals.length > 3 ? `
                    <div class="more-goals-indicator">
                        <a href="goals.html" class="view-more-link">
                            +${this.goals.length - 3} more goals
                        </a>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    renderDashboardGoalCard(goal) {
        const goalType = this.getGoalTypeInfo(goal.goal_type);
        const streak = this.streaks.find(s => s.goal_id === goal.id);
        const progress = goal.progress_percentage || 0;
        const isAchieved = goal.is_achieved_today || goal.is_achieved_this_week;
        
        return `
            <div class="dashboard-goal-card ${isAchieved ? 'achieved' : ''}" data-goal-id="${goal.id}">
                <div class="goal-card-header">
                    <div class="goal-icon">${goalType.icon}</div>
                    <div class="goal-title">
                        <div class="goal-name">${goalType.name}</div>
                        <div class="goal-target">${this.formatValue(goal.target_value, goalType.unit)} ${goalType.unit}</div>
                    </div>
                    <div class="goal-status ${isAchieved ? 'achieved' : 'pending'}">
                        ${isAchieved ? '✅' : '⏳'}
                    </div>
                </div>
                
                <div class="goal-card-progress">
                    <div class="progress-bar-mini">
                        <div class="progress-fill" style="width: ${Math.min(progress, 100)}%"></div>
                    </div>
                    <div class="progress-text">
                        ${Math.round(progress)}% • ${this.formatValue(goal.current_progress || 0, goalType.unit)}
                    </div>
                </div>
                
                ${streak && streak.current_count > 0 ? `
                    <div class="goal-card-streak">
                        <span class="streak-flame">🔥</span>
                        <span class="streak-count">${streak.current_count} day${streak.current_count !== 1 ? 's' : ''}</span>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    renderStreaksOverview() {
        const container = document.getElementById('streaks-overview-widget');
        if (!container) return;
        
        const activeStreaks = this.streaks.filter(s => s.current_count > 0);
        
        if (activeStreaks.length === 0) {
            container.innerHTML = `
                <div class="streaks-overview-widget">
                    <div class="widget-header">
                        <h3 class="widget-title">
                            <span class="widget-icon">🔥</span>
                            Streaks
                        </h3>
                    </div>
                    <div class="no-streaks-message">
                        <div class="no-streaks-icon">🔥</div>
                        <div class="no-streaks-text">No active streaks yet</div>
                        <div class="no-streaks-hint">Complete your goals to start building streaks!</div>
                    </div>
                </div>
            `;
            return;
        }
        
        // Sort streaks by count (longest first)
        const sortedStreaks = activeStreaks.sort((a, b) => b.current_count - a.current_count);
        
        container.innerHTML = `
            <div class="streaks-overview-widget">
                <div class="widget-header">
                    <h3 class="widget-title">
                        <span class="widget-icon">🔥</span>
                        Active Streaks
                    </h3>
                    <div class="streaks-count">${activeStreaks.length}</div>
                </div>
                
                <div class="streaks-list">
                    ${sortedStreaks.slice(0, 5).map(streak => this.renderStreakItem(streak)).join('')}
                </div>
                
                ${activeStreaks.length > 5 ? `
                    <div class="view-all-streaks">
                        <a href="goals.html" class="view-more-link">View all streaks</a>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    renderStreakItem(streak) {
        const goalType = this.getGoalTypeInfo(streak.goalInfo.goal_type);
        const flameIntensity = this.getFlameIntensity(streak.current_count);
        
        return `
            <div class="streak-item" data-goal-id="${streak.goal_id}">
                <div class="streak-flame ${flameIntensity}">${this.getFlameIcon(streak.current_count)}</div>
                <div class="streak-info">
                    <div class="streak-goal">${goalType.name}</div>
                    <div class="streak-count">${streak.current_count} day${streak.current_count !== 1 ? 's' : ''}</div>
                </div>
                <div class="streak-badge ${this.getStreakBadgeClass(streak.current_count)}">
                    ${this.getStreakBadge(streak.current_count)}
                </div>
            </div>
        `;
    }
    
    renderQuickActions() {
        const container = document.getElementById('goals-quick-actions');
        if (!container) return;
        
        container.innerHTML = `
            <div class="goals-quick-actions">
                <button class="quick-action-btn create-goal" data-action="create-goal">
                    <span class="action-icon">➕</span>
                    <span class="action-text">New Goal</span>
                </button>
                
                <button class="quick-action-btn manual-achievement" data-action="manual-achievement">
                    <span class="action-icon">✅</span>
                    <span class="action-text">Log Achievement</span>
                </button>
                
                <button class="quick-action-btn view-progress" data-action="view-progress">
                    <span class="action-icon">📊</span>
                    <span class="action-text">View Progress</span>
                </button>
            </div>
        `;
    }
    
    renderTodayProgressCards() {
        // Integrate goal progress with existing metric cards
        const metricsContainer = document.querySelector('.metrics-grid, .dashboard-metrics');
        if (!metricsContainer) return;
        
        // Find or create goals progress card
        let goalsCard = document.getElementById('goals-progress-card');
        if (!goalsCard) {
            goalsCard = document.createElement('div');
            goalsCard.id = 'goals-progress-card';
            goalsCard.className = 'metric-card goals-progress-card';
            metricsContainer.appendChild(goalsCard);
        }
        
        const todayAchievements = this.goals.filter(g => g.is_achieved_today).length;
        const totalGoals = this.goals.length;
        const completionRate = totalGoals > 0 ? (todayAchievements / totalGoals) * 100 : 0;
        
        goalsCard.innerHTML = `
            <div class="metric-card-header">
                <h3 class="metric-title">Goals Progress</h3>
                <div class="metric-icon">🎯</div>
            </div>
            
            <div class="metric-value-section">
                <div class="metric-main-value">${todayAchievements}/${totalGoals}</div>
                <div class="metric-subtitle">goals achieved today</div>
            </div>
            
            <div class="metric-progress-bar">
                <div class="progress-fill" style="width: ${completionRate}%"></div>
            </div>
            
            <div class="metric-details">
                <div class="metric-detail">
                    <span class="detail-label">Completion Rate</span>
                    <span class="detail-value">${Math.round(completionRate)}%</span>
                </div>
            </div>
            
            <div class="metric-actions">
                <button class="metric-action-btn" data-action="view-goals">
                    View All Goals
                </button>
            </div>
        `;
    }
    
    updateNavigationBadges() {
        // Update navigation badge for goals page
        const goalsNavLink = document.querySelector('a[href="goals.html"], .nav-link[href="goals.html"]');
        if (goalsNavLink) {
            const activeGoals = this.goals.filter(g => g.status === 'active').length;
            const existingBadge = goalsNavLink.querySelector('.nav-badge');
            
            if (activeGoals > 0) {
                if (!existingBadge) {
                    const badge = document.createElement('span');
                    badge.className = 'nav-badge';
                    badge.textContent = activeGoals;
                    goalsNavLink.appendChild(badge);
                } else {
                    existingBadge.textContent = activeGoals;
                }
            } else if (existingBadge) {
                existingBadge.remove();
            }
        }
    }
    
    setupEventListeners() {
        // Quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action]')) {
                const action = e.target.closest('[data-action]').dataset.action;
                this.handleQuickAction(action, e.target);
            }
        });
        
        // Goal card clicks
        document.addEventListener('click', (e) => {
            const goalCard = e.target.closest('.dashboard-goal-card');
            if (goalCard) {
                const goalId = goalCard.dataset.goalId;
                this.handleGoalCardClick(goalId);
            }
        });
        
        // Streak item clicks
        document.addEventListener('click', (e) => {
            const streakItem = e.target.closest('.streak-item');
            if (streakItem) {
                const goalId = streakItem.dataset.goalId;
                this.handleStreakItemClick(goalId);
            }
        });
        
        // Listen for goal updates
        document.addEventListener('goal:updated', () => {
            this.refresh();
        });
        
        document.addEventListener('achievement:added', () => {
            this.refresh();
        });
    }
    
    handleQuickAction(action, element) {
        switch (action) {
            case 'create-goal':
                this.openGoalCreation();
                break;
            case 'manual-achievement':
                this.openManualAchievement();
                break;
            case 'view-progress':
            case 'view-goals':
                window.location.href = 'goals.html';
                break;
            default:
                console.log('Unknown quick action:', action);
        }
    }
    
    handleGoalCardClick(goalId) {
        // Navigate to goal details or goals page
        window.location.href = `goals.html#goal-${goalId}`;
    }
    
    handleStreakItemClick(goalId) {
        // Navigate to goal details with streak focus
        window.location.href = `goals.html#goal-${goalId}-streak`;
    }
    
    openGoalCreation() {
        // If goals page modal system is available, use it
        if (window.goalsManager && window.goalsManager.showGoalModal) {
            window.goalsManager.showGoalModal();
        } else {
            // Otherwise navigate to goals page
            window.location.href = 'goals.html#create';
        }
    }
    
    openManualAchievement() {
        // Show manual achievement modal or navigate
        if (this.goals.length === 0) {
            this.showNotification('Create a goal first to log achievements', 'info');
            return;
        }
        
        // Simple implementation - could be enhanced with modal
        const goalOptions = this.goals.map(g => {
            const goalType = this.getGoalTypeInfo(g.goal_type);
            return `<option value="${g.id}">${goalType.name}</option>`;
        }).join('');
        
        const goalId = prompt(`Select goal to log achievement for:\n${this.goals.map((g, i) => `${i + 1}. ${this.getGoalTypeInfo(g.goal_type).name}`).join('\n')}`);
        
        if (goalId && !isNaN(goalId) && goalId > 0 && goalId <= this.goals.length) {
            const selectedGoal = this.goals[goalId - 1];
            this.logManualAchievement(selectedGoal);
        }
    }
    
    async logManualAchievement(goal) {
        try {
            const value = prompt(`Enter achievement value for ${this.getGoalTypeInfo(goal.goal_type).name}:`);
            if (!value || isNaN(value)) return;
            
            const response = await fetch(`${this.progressBase}/goal/${goal.id}/manual-achievement`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    actual_value: parseFloat(value),
                    notes: 'Manual entry from dashboard'
                })
            });
            
            if (response.ok) {
                this.showNotification('Achievement logged successfully!', 'success');
                this.refresh();
            } else {
                throw new Error('Failed to log achievement');
            }
        } catch (error) {
            console.error('Error logging manual achievement:', error);
            this.showNotification('Failed to log achievement', 'error');
        }
    }
    
    startPeriodicUpdates() {
        // Refresh data every 5 minutes
        setInterval(() => {
            this.refresh();
        }, 5 * 60 * 1000);
        
        // Quick refresh every minute for real-time updates
        setInterval(() => {
            this.quickRefresh();
        }, 60 * 1000);
    }
    
    async refresh() {
        await this.loadDashboardData();
        this.renderGoalsWidgets();
    }
    
    async quickRefresh() {
        // Light refresh for progress updates only
        try {
            const progressResponse = await fetch(`${this.progressBase}/dashboard`);
            if (progressResponse.ok) {
                this.todayProgress = await progressResponse.json();
                this.updateProgressIndicators();
            }
        } catch (error) {
            console.error('Error in quick refresh:', error);
        }
    }
    
    updateProgressIndicators() {
        // Update progress bars and values without full re-render
        this.goals.forEach(goal => {
            const goalCard = document.querySelector(`[data-goal-id="${goal.id}"]`);
            if (goalCard) {
                const progressFill = goalCard.querySelector('.progress-fill');
                const progressText = goalCard.querySelector('.progress-text');
                
                if (progressFill && progressText) {
                    const progress = goal.progress_percentage || 0;
                    progressFill.style.width = `${Math.min(progress, 100)}%`;
                    progressText.textContent = `${Math.round(progress)}% • ${this.formatValue(goal.current_progress || 0, this.getGoalTypeInfo(goal.goal_type).unit)}`;
                }
            }
        });
    }
    
    // Helper methods
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
    
    getFlameIntensity(streakCount) {
        if (streakCount >= 100) return 'legendary';
        if (streakCount >= 50) return 'epic';
        if (streakCount >= 30) return 'hot';
        if (streakCount >= 14) return 'warm';
        if (streakCount >= 7) return 'medium';
        return 'small';
    }
    
    getFlameIcon(streakCount) {
        if (streakCount >= 50) return '🔥';
        if (streakCount >= 14) return '🔥';
        if (streakCount >= 7) return '🔥';
        return '🔥';
    }
    
    getStreakBadgeClass(streakCount) {
        if (streakCount >= 100) return 'legendary';
        if (streakCount >= 50) return 'epic';
        if (streakCount >= 30) return 'excellent';
        if (streakCount >= 14) return 'great';
        if (streakCount >= 7) return 'good';
        return 'building';
    }
    
    getStreakBadge(streakCount) {
        if (streakCount >= 100) return 'LEGEND';
        if (streakCount >= 50) return 'EPIC';
        if (streakCount >= 30) return 'AMAZING';
        if (streakCount >= 14) return 'GREAT';
        if (streakCount >= 7) return 'GOOD';
        return 'BUILDING';
    }
    
    showNotification(message, type = 'info') {
        // Simple notification - could be enhanced with a proper notification system
        const notification = document.createElement('div');
        notification.className = `dashboard-notification ${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 100);
        
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => notification.remove());
        
        setTimeout(() => notification.remove(), 5000);
    }
}

// Initialize dashboard goals integration
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardGoals = new DashboardGoals();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardGoals;
}