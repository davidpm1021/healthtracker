/**
 * Goals Management - Health Tracker
 * Frontend JavaScript for goal creation, editing, and management
 */

class GoalsManager {
    constructor() {
        this.goals = [];
        this.currentGoal = null;
        this.apiBase = '/api/goals';
        this.progressBase = '/api/progress';
        
        this.goalTypes = {
            'steps': {
                name: 'Daily Steps',
                unit: 'steps',
                icon: '👟',
                defaultTarget: 10000,
                description: 'Track your daily step count'
            },
            'sleep_duration': {
                name: 'Sleep Duration',
                unit: 'hours',
                icon: '😴',
                defaultTarget: 8,
                description: 'Monitor your sleep duration'
            },
            'weight_logging': {
                name: 'Weight Logging',
                unit: 'entries',
                icon: '⚖️',
                defaultTarget: 1,
                description: 'Log your weight regularly'
            },
            'hrv_entry': {
                name: 'HRV Entry',
                unit: 'entries',
                icon: '❤️',
                defaultTarget: 1,
                description: 'Record HRV measurements'
            },
            'heart_rate_zone': {
                name: 'Heart Rate Zone',
                unit: 'minutes',
                icon: '💗',
                defaultTarget: 30,
                description: 'Time in target heart rate zones'
            }
        };
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadGoals();
        this.renderGoals();
    }
    
    setupEventListeners() {
        // Goal creation button
        const createBtn = document.getElementById('create-goal-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showGoalModal());
        }
        
        // Modal close buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-close') || 
                e.target.classList.contains('modal-backdrop')) {
                this.hideGoalModal();
            }
        });
        
        // Form submission
        const goalForm = document.getElementById('goal-form');
        if (goalForm) {
            goalForm.addEventListener('submit', (e) => this.handleGoalSubmit(e));
        }
        
        // Goal type selection
        const goalTypeSelect = document.getElementById('goal-type');
        if (goalTypeSelect) {
            goalTypeSelect.addEventListener('change', (e) => this.handleGoalTypeChange(e));
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-goals-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshGoals());
        }
    }
    
    async loadGoals() {
        try {
            const response = await fetch(`${this.apiBase}?include_progress=true`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.goals = await response.json();
            console.log('Loaded goals:', this.goals);
            
        } catch (error) {
            console.error('Error loading goals:', error);
            this.showError('Failed to load goals. Please try again.');
        }
    }
    
    renderGoals() {
        const container = document.getElementById('goals-container');
        if (!container) return;
        
        if (this.goals.length === 0) {
            container.innerHTML = this.renderEmptyState();
            return;
        }
        
        const goalsHtml = this.goals.map(goal => this.renderGoalCard(goal)).join('');
        container.innerHTML = `
            <div class="goals-grid">
                ${goalsHtml}
            </div>
        `;
        
        // Add event listeners to goal cards
        this.setupGoalCardListeners();
    }
    
    renderGoalCard(goal) {
        const goalType = this.goalTypes[goal.goal_type] || {};
        const progress = goal.current_progress || 0;
        const progressPercentage = goal.progress_percentage || 0;
        const isAchievedToday = goal.is_achieved_today || false;
        const isAchievedThisWeek = goal.is_achieved_this_week || false;
        
        const statusClass = goal.status === 'active' ? 'active' : 'inactive';
        const achievementStatus = goal.frequency === 'daily' ? isAchievedToday : isAchievedThisWeek;
        const achievementText = goal.frequency === 'daily' ? 'Today' : 'This Week';
        
        return `
            <div class="goal-card ${statusClass}" data-goal-id="${goal.id}">
                <div class="goal-header">
                    <div class="goal-icon">${goalType.icon || '🎯'}</div>
                    <div class="goal-title">
                        <h3>${goalType.name || goal.goal_type}</h3>
                        <span class="goal-frequency">${goal.frequency}</span>
                    </div>
                    <div class="goal-actions">
                        <button class="btn-icon edit-goal" data-goal-id="${goal.id}" title="Edit Goal">
                            ✏️
                        </button>
                        <button class="btn-icon delete-goal" data-goal-id="${goal.id}" title="Delete Goal">
                            🗑️
                        </button>
                    </div>
                </div>
                
                <div class="goal-progress">
                    <div class="progress-info">
                        <span class="current-value">${this.formatValue(progress, goalType.unit)}</span>
                        <span class="target-value">/ ${this.formatValue(goal.target_value, goalType.unit)}</span>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${Math.min(progressPercentage, 100)}%"></div>
                    </div>
                    
                    <div class="progress-percentage">${Math.round(progressPercentage)}%</div>
                </div>
                
                <div class="goal-status">
                    <div class="achievement-badge ${achievementStatus ? 'achieved' : 'pending'}">
                        ${achievementStatus ? '✅' : '⏳'} ${achievementText}
                    </div>
                    
                    <div class="goal-streak" data-goal-id="${goal.id}">
                        <span class="streak-loading">Loading streak...</span>
                    </div>
                </div>
                
                <div class="goal-footer">
                    <small class="goal-description">${goalType.description || ''}</small>
                    <button class="btn-link view-details" data-goal-id="${goal.id}">
                        View Details
                    </button>
                </div>
            </div>
        `;
    }
    
    renderEmptyState() {
        return `
            <div class="empty-state">
                <div class="empty-icon">🎯</div>
                <h3>No Goals Yet</h3>
                <p>Create your first health goal to start tracking your progress.</p>
                <button class="btn btn-primary" onclick="goalsManager.showGoalModal()">
                    Create Your First Goal
                </button>
            </div>
        `;
    }
    
    setupGoalCardListeners() {
        // Edit goal buttons
        document.querySelectorAll('.edit-goal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const goalId = parseInt(e.target.dataset.goalId);
                this.editGoal(goalId);
            });
        });
        
        // Delete goal buttons
        document.querySelectorAll('.delete-goal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const goalId = parseInt(e.target.dataset.goalId);
                this.deleteGoal(goalId);
            });
        });
        
        // View details buttons
        document.querySelectorAll('.view-details').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const goalId = parseInt(e.target.dataset.goalId);
                this.viewGoalDetails(goalId);
            });
        });
        
        // Load streak information for each goal
        this.loadStreaksForGoals();
    }
    
    async loadStreaksForGoals() {
        for (const goal of this.goals) {
            try {
                const response = await fetch(`${this.apiBase}/${goal.id}/streak`);
                if (response.ok) {
                    const streak = await response.json();
                    this.updateStreakDisplay(goal.id, streak);
                }
            } catch (error) {
                console.error(`Error loading streak for goal ${goal.id}:`, error);
                this.updateStreakDisplay(goal.id, null);
            }
        }
    }
    
    updateStreakDisplay(goalId, streak) {
        const streakElement = document.querySelector(`.goal-streak[data-goal-id="${goalId}"]`);
        if (!streakElement) return;
        
        if (!streak || streak.current_count === 0) {
            streakElement.innerHTML = '<span class="streak-none">No streak</span>';
        } else {
            const streakText = streak.current_count === 1 ? 'day' : 'days';
            const streakClass = streak.current_count >= 7 ? 'streak-good' : 'streak-building';
            
            streakElement.innerHTML = `
                <span class="streak-count ${streakClass}">
                    🔥 ${streak.current_count} ${streakText}
                </span>
            `;
        }
    }
    
    showGoalModal(goal = null) {
        this.currentGoal = goal;
        const modal = document.getElementById('goal-modal');
        const form = document.getElementById('goal-form');
        const title = document.getElementById('modal-title');
        
        if (!modal || !form) return;
        
        // Reset form
        form.reset();
        
        if (goal) {
            // Edit mode
            title.textContent = 'Edit Goal';
            this.populateForm(goal);
        } else {
            // Create mode
            title.textContent = 'Create New Goal';
            this.populateFormDefaults();
        }
        
        modal.classList.add('active');
        document.body.classList.add('modal-open');
    }
    
    hideGoalModal() {
        const modal = document.getElementById('goal-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
        this.currentGoal = null;
    }
    
    populateForm(goal) {
        document.getElementById('goal-type').value = goal.goal_type;
        document.getElementById('target-value').value = goal.target_value;
        document.getElementById('frequency').value = goal.frequency;
        document.getElementById('status').value = goal.status;
        document.getElementById('description').value = goal.description || '';
        
        this.handleGoalTypeChange({ target: { value: goal.goal_type } });
    }
    
    populateFormDefaults() {
        document.getElementById('goal-type').value = 'steps';
        document.getElementById('frequency').value = 'daily';
        document.getElementById('status').value = 'active';
        
        this.handleGoalTypeChange({ target: { value: 'steps' } });
    }
    
    handleGoalTypeChange(e) {
        const goalType = e.target.value;
        const goalInfo = this.goalTypes[goalType];
        
        if (goalInfo) {
            // Update target value if it's default/empty
            const targetInput = document.getElementById('target-value');
            if (!targetInput.value || targetInput.value == targetInput.defaultValue) {
                targetInput.value = goalInfo.defaultTarget;
            }
            
            // Update unit display
            const unitDisplay = document.getElementById('target-unit');
            if (unitDisplay) {
                unitDisplay.textContent = goalInfo.unit;
            }
            
            // Update description placeholder
            const descInput = document.getElementById('description');
            if (descInput) {
                descInput.placeholder = goalInfo.description;
            }
        }
    }
    
    async handleGoalSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const goalData = {
            goal_type: formData.get('goal_type'),
            target_value: parseFloat(formData.get('target_value')),
            frequency: formData.get('frequency'),
            status: formData.get('status'),
            description: formData.get('description') || null
        };
        
        // Validation
        if (!goalData.goal_type || !goalData.target_value || goalData.target_value <= 0) {
            this.showError('Please fill in all required fields with valid values.');
            return;
        }
        
        try {
            let response;
            if (this.currentGoal) {
                // Update existing goal
                response = await fetch(`${this.apiBase}/${this.currentGoal.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(goalData)
                });
            } else {
                // Create new goal
                response = await fetch(this.apiBase, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(goalData)
                });
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to save goal');
            }
            
            const savedGoal = await response.json();
            console.log('Goal saved:', savedGoal);
            
            this.hideGoalModal();
            await this.refreshGoals();
            this.showSuccess(this.currentGoal ? 'Goal updated successfully!' : 'Goal created successfully!');
            
        } catch (error) {
            console.error('Error saving goal:', error);
            this.showError(error.message || 'Failed to save goal. Please try again.');
        }
    }
    
    async editGoal(goalId) {
        const goal = this.goals.find(g => g.id === goalId);
        if (goal) {
            this.showGoalModal(goal);
        } else {
            this.showError('Goal not found');
        }
    }
    
    async deleteGoal(goalId) {
        const goal = this.goals.find(g => g.id === goalId);
        if (!goal) {
            this.showError('Goal not found');
            return;
        }
        
        const confirmed = confirm(`Are you sure you want to delete the goal "${this.goalTypes[goal.goal_type]?.name || goal.goal_type}"? This action cannot be undone.`);
        if (!confirmed) return;
        
        try {
            const response = await fetch(`${this.apiBase}/${goalId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to delete goal');
            }
            
            await this.refreshGoals();
            this.showSuccess('Goal deleted successfully!');
            
        } catch (error) {
            console.error('Error deleting goal:', error);
            this.showError(error.message || 'Failed to delete goal. Please try again.');
        }
    }
    
    async viewGoalDetails(goalId) {
        // Navigate to goal details page or show detailed modal
        window.location.href = `#/goals/${goalId}`;
    }
    
    async refreshGoals() {
        const refreshBtn = document.getElementById('refresh-goals-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.textContent = 'Refreshing...';
        }
        
        try {
            await this.loadGoals();
            this.renderGoals();
        } finally {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.textContent = 'Refresh';
            }
        }
    }
    
    formatValue(value, unit) {
        if (typeof value !== 'number') return '0';
        
        if (unit === 'steps') {
            return value.toLocaleString();
        } else if (unit === 'hours') {
            return `${value.toFixed(1)}h`;
        } else if (unit === 'minutes') {
            return `${Math.round(value)}min`;
        } else if (unit === 'entries') {
            return Math.round(value).toString();
        } else {
            return value.toString();
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after delay
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
        
        // Handle close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.goalsManager = new GoalsManager();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GoalsManager;
}