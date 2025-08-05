/**
 * Streak Calendar Component - Health Tracker
 * Calendar-based visualization of streak achievements and patterns
 */

class StreakCalendar {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            goalId: null,
            showMonths: 6,
            showFreezeTokens: true,
            showTooltips: true,
            allowNavigation: true,
            ...options
        };
        
        this.achievements = [];
        this.freezeTokens = [];
        this.currentDate = new Date();
        this.viewDate = new Date();
        this.apiBase = '/api/goals';
        this.progressBase = '/api/progress';
        
        this.init();
    }
    
    async init() {
        if (!this.container) {
            console.error('Streak calendar container not found');
            return;
        }
        
        if (this.options.goalId) {
            await this.loadData();
        }
        
        this.render();
        this.setupEventListeners();
    }
    
    async loadData() {
        try {
            // Load achievements
            const achievementsResponse = await fetch(
                `${this.progressBase}/achievements/${this.options.goalId}?limit=365`
            );
            if (achievementsResponse.ok) {
                this.achievements = await achievementsResponse.json();
            }
            
            // Load freeze tokens if needed
            if (this.options.showFreezeTokens) {
                const tokensResponse = await fetch(
                    `${this.apiBase}/${this.options.goalId}/freeze-tokens`
                );
                if (tokensResponse.ok) {
                    this.freezeTokens = await tokensResponse.json();
                }
            }
            
        } catch (error) {
            console.error('Error loading calendar data:', error);
        }
    }
    
    render() {
        const calendarHtml = this.generateCalendarHTML();
        this.container.innerHTML = `
            <div class="streak-calendar">
                ${this.options.allowNavigation ? this.renderNavigation() : ''}
                <div class="calendar-container">
                    ${calendarHtml}
                </div>
                ${this.renderLegend()}
            </div>
        `;
        
        this.attachTooltips();
    }
    
    renderNavigation() {
        return `
            <div class="calendar-navigation">
                <button class="nav-btn prev" data-action="prev">
                    ← Previous
                </button>
                <div class="nav-period">
                    <span class="nav-date">${this.formatViewPeriod()}</span>
                </div>
                <button class="nav-btn next" data-action="next">
                    Next →
                </button>
            </div>
        `;
    }
    
    generateCalendarHTML() {
        let html = '';
        const endDate = new Date(this.viewDate);
        const startDate = new Date(endDate);
        startDate.setMonth(startDate.getMonth() - this.options.showMonths + 1);
        
        // Generate month-by-month calendars
        let currentMonth = new Date(startDate);
        while (currentMonth <= endDate) {
            html += this.renderMonth(currentMonth);
            currentMonth.setMonth(currentMonth.getMonth() + 1);
        }
        
        return html;
    }
    
    renderMonth(monthDate) {
        const year = monthDate.getFullYear();
        const month = monthDate.getMonth();
        const monthName = monthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        
        // Get first day of month and number of days
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        
        let monthHtml = `
            <div class="calendar-month">
                <div class="month-header">
                    <h3 class="month-title">${monthName}</h3>
                </div>
                <div class="calendar-grid">
                    <div class="weekday-headers">
                        <div class="weekday">S</div>
                        <div class="weekday">M</div>
                        <div class="weekday">T</div>
                        <div class="weekday">W</div>
                        <div class="weekday">T</div>
                        <div class="weekday">F</div>
                        <div class="weekday">S</div>
                    </div>
                    <div class="calendar-days">
        `;
        
        // Add empty cells for days before the first of the month
        for (let i = 0; i < startingDayOfWeek; i++) {
            monthHtml += '<div class="calendar-day empty"></div>';
        }
        
        // Add days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            const dayData = this.getDayData(date);
            monthHtml += this.renderDay(date, dayData);
        }
        
        monthHtml += `
                    </div>
                </div>
            </div>
        `;
        
        return monthHtml;
    }
    
    renderDay(date, dayData) {
        const dateStr = date.toISOString().split('T')[0];
        const isToday = this.isSameDay(date, this.currentDate);
        const isFuture = date > this.currentDate;
        
        let classes = ['calendar-day'];
        let content = date.getDate();
        let tooltip = this.formatDate(date);
        
        if (isToday) classes.push('today');
        if (isFuture) classes.push('future');
        
        // Achievement status
        if (dayData.achieved) {
            classes.push('achieved');
            tooltip += '\n✅ Goal achieved';
        } else if (!isFuture) {
            classes.push('missed');
            tooltip += '\n❌ Goal missed';
        }
        
        // Freeze token usage
        if (dayData.freezeTokenUsed) {
            classes.push('freeze-token-used');
            tooltip += '\n🛡️ Freeze token used';
            content += '<div class="freeze-token-indicator">🛡️</div>';
        }
        
        // Streak status
        if (dayData.streakDay) {
            classes.push(`streak-day-${Math.min(dayData.streakDay, 7)}`);
            tooltip += `\n🔥 Day ${dayData.streakDay} of streak`;
        }
        
        // Milestone days
        if (dayData.milestone) {
            classes.push('milestone');
            tooltip += `\n🎉 ${dayData.milestone}-day milestone!`;
            content += '<div class="milestone-indicator">🎉</div>';
        }
        
        return `
            <div class="${classes.join(' ')}" 
                 data-date="${dateStr}" 
                 data-tooltip="${tooltip}"
                 role="gridcell"
                 tabindex="0">
                ${content}
            </div>
        `;
    }
    
    getDayData(date) {
        const dateStr = date.toISOString().split('T')[0];
        
        // Check if goal was achieved on this date
        const achievement = this.achievements.find(a => 
            a.achieved_date === dateStr
        );
        
        // Check for freeze token usage
        const freezeToken = this.freezeTokens.find(t => 
            t.used_date === dateStr
        );
        
        // Calculate streak information
        const streakInfo = this.calculateStreakForDate(date);
        
        return {
            achieved: !!achievement,
            freezeTokenUsed: !!freezeToken,
            streakDay: streakInfo.day,
            milestone: streakInfo.milestone,
            achievement: achievement,
            freezeToken: freezeToken
        };
    }
    
    calculateStreakForDate(targetDate) {
        // Sort achievements by date
        const sortedAchievements = this.achievements
            .map(a => new Date(a.achieved_date))
            .sort((a, b) => a - b);
        
        if (sortedAchievements.length === 0) {
            return { day: 0, milestone: null };
        }
        
        // Find consecutive streak up to target date
        let streakCount = 0;
        let checkDate = new Date(targetDate);
        
        // Work backwards to count consecutive days
        while (checkDate >= sortedAchievements[0]) {
            const hasAchievement = sortedAchievements.some(achievementDate => 
                this.isSameDay(achievementDate, checkDate)
            );
            
            if (hasAchievement) {
                streakCount++;
                checkDate.setDate(checkDate.getDate() - 1);
            } else {
                break;
            }
        }
        
        // Check if this is a milestone day
        const milestones = [7, 14, 30, 50, 100, 200, 365];
        const milestone = milestones.find(m => m === streakCount);
        
        return {
            day: streakCount,
            milestone: milestone
        };
    }
    
    renderLegend() {
        return `
            <div class="calendar-legend">
                <div class="legend-title">Legend</div>
                <div class="legend-items">
                    <div class="legend-item">
                        <div class="legend-color achieved"></div>
                        <span>Goal Achieved</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color missed"></div>
                        <span>Goal Missed</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color freeze-token-used"></div>
                        <span>Freeze Token Used</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color milestone"></div>
                        <span>Milestone Reached</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color today"></div>
                        <span>Today</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    attachTooltips() {
        if (!this.options.showTooltips) return;
        
        const days = this.container.querySelectorAll('.calendar-day[data-tooltip]');
        days.forEach(day => {
            day.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });
            
            day.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }
    
    showTooltip(element, content) {
        this.hideTooltip(); // Remove any existing tooltip
        
        const tooltip = document.createElement('div');
        tooltip.className = 'calendar-tooltip';
        tooltip.innerHTML = content.replace(/\n/g, '<br>');
        
        document.body.appendChild(tooltip);
        
        // Position tooltip
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 8;
        
        // Adjust if tooltip goes off screen
        if (left < 0) left = 8;
        if (left + tooltipRect.width > window.innerWidth) {
            left = window.innerWidth - tooltipRect.width - 8;
        }
        if (top < 0) {
            top = rect.bottom + 8;
        }
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
        tooltip.classList.add('show');
    }
    
    hideTooltip() {
        const existingTooltip = document.querySelector('.calendar-tooltip');
        if (existingTooltip) {
            existingTooltip.remove();
        }
    }
    
    setupEventListeners() {
        // Navigation buttons
        if (this.options.allowNavigation) {
            this.container.addEventListener('click', (e) => {
                if (e.target.classList.contains('nav-btn')) {
                    const action = e.target.dataset.action;
                    this.navigate(action);
                }
            });
        }
        
        // Day clicks
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('calendar-day') && !e.target.classList.contains('empty')) {
                const date = e.target.dataset.date;
                this.handleDayClick(date);
            }
        });
        
        // Keyboard navigation
        this.container.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('calendar-day')) {
                this.handleKeyNavigation(e);
            }
        });
    }
    
    navigate(action) {
        if (action === 'prev') {
            this.viewDate.setMonth(this.viewDate.getMonth() - 1);
        } else if (action === 'next') {
            this.viewDate.setMonth(this.viewDate.getMonth() + 1);
        }
        
        this.loadData().then(() => this.render());
    }
    
    handleDayClick(dateStr) {
        const date = new Date(dateStr);
        const dayData = this.getDayData(date);
        
        // Emit custom event for day selection
        const event = new CustomEvent('daySelected', {
            detail: {
                date: date,
                dateString: dateStr,
                data: dayData
            }
        });
        
        this.container.dispatchEvent(event);
    }
    
    handleKeyNavigation(e) {
        const currentDay = e.target;
        const currentDate = new Date(currentDay.dataset.date);
        let newDate;
        
        switch (e.key) {
            case 'ArrowLeft':
                newDate = new Date(currentDate);
                newDate.setDate(newDate.getDate() - 1);
                break;
            case 'ArrowRight':
                newDate = new Date(currentDate);
                newDate.setDate(newDate.getDate() + 1);
                break;
            case 'ArrowUp':
                newDate = new Date(currentDate);
                newDate.setDate(newDate.getDate() - 7);
                break;
            case 'ArrowDown':
                newDate = new Date(currentDate);
                newDate.setDate(newDate.getDate() + 7);
                break;
        }
        
        if (newDate) {
            e.preventDefault();
            const newDateStr = newDate.toISOString().split('T')[0];
            const newDayElement = this.container.querySelector(`[data-date="${newDateStr}"]`);
            if (newDayElement) {
                newDayElement.focus();
            }
        }
    }
    
    formatViewPeriod() {
        const endDate = new Date(this.viewDate);
        const startDate = new Date(endDate);
        startDate.setMonth(startDate.getMonth() - this.options.showMonths + 1);
        
        if (this.options.showMonths === 1) {
            return this.viewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        } else {
            return `${startDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`;
        }
    }
    
    formatDate(date) {
        return date.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
    
    isSameDay(date1, date2) {
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getDate() === date2.getDate();
    }
    
    // Public methods
    async refresh() {
        await this.loadData();
        this.render();
    }
    
    setGoal(goalId) {
        this.options.goalId = goalId;
        this.loadData().then(() => this.render());
    }
    
    goToToday() {
        this.viewDate = new Date();
        this.loadData().then(() => this.render());
    }
    
    goToDate(date) {
        this.viewDate = new Date(date);
        this.loadData().then(() => this.render());
    }
    
    destroy() {
        this.hideTooltip();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreakCalendar;
}

// Global registration
window.StreakCalendar = StreakCalendar;