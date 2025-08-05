/**
 * Streak Analytics Component - Health Tracker
 * Advanced analytics and insights for streak performance
 */

class StreakAnalytics {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            goalId: null,
            period: 'last_90_days', // last_30_days, last_90_days, last_year, all_time
            showPatterns: true,
            showPredictions: true,
            showComparisons: true,
            ...options
        };
        
        this.analytics = null;
        this.achievements = [];
        this.streaks = [];
        this.apiBase = '/api/goals';
        this.progressBase = '/api/progress';
        
        this.init();
    }
    
    async init() {
        if (!this.container) {
            console.error('Streak analytics container not found');
            return;
        }
        
        if (this.options.goalId) {
            await this.loadAnalyticsData();
        }
        
        this.render();
        this.setupEventListeners();
    }
    
    async loadAnalyticsData() {
        try {
            // Load achievement data
            const achievementsResponse = await fetch(
                `${this.progressBase}/achievements/${this.options.goalId}?limit=365`
            );
            if (achievementsResponse.ok) {
                this.achievements = await achievementsResponse.json();
            }
            
            // Load streak summary
            const streakResponse = await fetch(`${this.apiBase}/${this.options.goalId}/streak`);
            if (streakResponse.ok) {
                const currentStreak = await streakResponse.json();
                this.streaks = [currentStreak]; // In a real app, this might be historical streaks
            }
            
            // Calculate analytics
            this.analytics = this.calculateAnalytics();
            
        } catch (error) {
            console.error('Error loading analytics data:', error);
        }
    }
    
    calculateAnalytics() {
        const now = new Date();
        const periodDays = this.getPeriodDays();
        const startDate = new Date(now);
        startDate.setDate(startDate.getDate() - periodDays);
        
        // Filter achievements to period
        const periodAchievements = this.achievements.filter(a => {
            const achievementDate = new Date(a.achieved_date);
            return achievementDate >= startDate && achievementDate <= now;
        });
        
        return {
            summary: this.calculateSummaryStats(periodAchievements, periodDays),
            patterns: this.calculatePatterns(periodAchievements),
            streaks: this.calculateStreakStats(periodAchievements),
            predictions: this.calculatePredictions(periodAchievements),
            comparisons: this.calculateComparisons(periodAchievements)
        };
    }
    
    calculateSummaryStats(achievements, totalDays) {
        const achievementDays = achievements.length;
        const consistencyRate = (achievementDays / totalDays) * 100;
        
        // Calculate longest streak in period
        const longestStreak = this.findLongestStreakInPeriod(achievements);
        
        // Calculate average value
        const totalValue = achievements.reduce((sum, a) => sum + a.actual_value, 0);
        const averageValue = achievementDays > 0 ? totalValue / achievementDays : 0;
        
        // Calculate trend
        const trend = this.calculateTrend(achievements);
        
        return {
            totalDays,
            achievementDays,
            consistencyRate,
            longestStreak,
            averageValue,
            trend,
            missedDays: totalDays - achievementDays
        };
    }
    
    calculatePatterns(achievements) {
        // Day of week patterns
        const dayOfWeekStats = this.calculateDayOfWeekPattern(achievements);
        
        // Time-based patterns (would need time data from achievements)
        const monthlyPattern = this.calculateMonthlyPattern(achievements);
        
        // Streak patterns
        const streakPatterns = this.calculateStreakPatterns(achievements);
        
        return {
            dayOfWeek: dayOfWeekStats,
            monthly: monthlyPattern,
            streaks: streakPatterns
        };
    }
    
    calculateStreakStats(achievements) {
        const streaks = this.findAllStreaks(achievements);
        
        if (streaks.length === 0) {
            return {
                count: 0,
                average: 0,
                longest: 0,
                current: 0,
                distribution: {}
            };
        }
        
        const lengths = streaks.map(s => s.length);
        const totalLength = lengths.reduce((sum, length) => sum + length, 0);
        
        // Distribution by length
        const distribution = {};
        for (const length of lengths) {
            const bucket = this.getStreakBucket(length);
            distribution[bucket] = (distribution[bucket] || 0) + 1;
        }
        
        return {
            count: streaks.length,
            average: totalLength / streaks.length,
            longest: Math.max(...lengths),
            current: this.streaks[0]?.current_count || 0,
            distribution
        };
    }
    
    calculatePredictions(achievements) {
        // Simple prediction based on recent trends
        const recentAchievements = achievements.slice(-14); // Last 14 days
        const recentRate = recentAchievements.length / 14;
        
        // Predict next 7 days
        const nextWeekPrediction = Math.round(recentRate * 7);
        
        // Predict streak continuation probability
        const streakContinuationProb = this.calculateStreakContinuationProbability(achievements);
        
        // Predict next milestone
        const nextMilestone = this.predictNextMilestone();
        
        return {
            nextWeekAchievements: nextWeekPrediction,
            streakContinuationProbability: streakContinuationProb,
            nextMilestone,
            confidenceLevel: this.calculatePredictionConfidence(achievements)
        };
    }
    
    calculateComparisons(achievements) {
        // Compare with previous period
        const currentPeriodDays = this.getPeriodDays();
        const previousPeriodStart = new Date();
        previousPeriodStart.setDate(previousPeriodStart.getDate() - (currentPeriodDays * 2));
        const previousPeriodEnd = new Date();
        previousPeriodEnd.setDate(previousPeriodEnd.getDate() - currentPeriodDays);
        
        const previousAchievements = this.achievements.filter(a => {
            const date = new Date(a.achieved_date);
            return date >= previousPeriodStart && date <= previousPeriodEnd;
        });
        
        const currentRate = (achievements.length / currentPeriodDays) * 100;
        const previousRate = (previousAchievements.length / currentPeriodDays) * 100;
        const rateChange = currentRate - previousRate;
        
        return {
            currentPeriodRate: currentRate,
            previousPeriodRate: previousRate,
            rateChange,
            improvement: rateChange > 0
        };
    }
    
    render() {
        if (!this.analytics) {
            this.renderLoading();
            return;
        }
        
        this.container.innerHTML = `
            <div class="streak-analytics">
                ${this.renderSummarySection()}
                ${this.options.showPatterns ? this.renderPatternsSection() : ''}
                ${this.options.showPredictions ? this.renderPredictionsSection() : ''}
                ${this.options.showComparisons ? this.renderComparisonsSection() : ''}
            </div>
        `;
        
        this.renderCharts();
    }
    
    renderLoading() {
        this.container.innerHTML = `
            <div class="analytics-loading">
                <div class="loading-spinner"></div>
                <div class="loading-text">Analyzing your streak data...</div>
            </div>
        `;
    }
    
    renderSummarySection() {
        const { summary } = this.analytics;
        const trendIcon = summary.trend > 0 ? '📈' : summary.trend < 0 ? '📉' : '➡️';
        const trendClass = summary.trend > 0 ? 'positive' : summary.trend < 0 ? 'negative' : 'neutral';
        
        return `
            <div class="analytics-section summary">
                <h3 class="section-title">Performance Summary</h3>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="summary-value">${Math.round(summary.consistencyRate)}%</div>
                        <div class="summary-label">Consistency Rate</div>
                        <div class="summary-detail">${summary.achievementDays} out of ${summary.totalDays} days</div>
                    </div>
                    
                    <div class="summary-card">
                        <div class="summary-value">${summary.longestStreak}</div>
                        <div class="summary-label">Longest Streak</div>
                        <div class="summary-detail">days in a row</div>
                    </div>
                    
                    <div class="summary-card">
                        <div class="summary-value">${this.formatValue(summary.averageValue)}</div>
                        <div class="summary-label">Average Performance</div>
                        <div class="summary-detail">per achievement day</div>
                    </div>
                    
                    <div class="summary-card ${trendClass}">
                        <div class="summary-value">${trendIcon} ${Math.abs(summary.trend).toFixed(1)}%</div>
                        <div class="summary-label">Trend</div>
                        <div class="summary-detail">${summary.trend > 0 ? 'improving' : summary.trend < 0 ? 'declining' : 'stable'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderPatternsSection() {
        const { patterns } = this.analytics;
        
        return `
            <div class="analytics-section patterns">
                <h3 class="section-title">Performance Patterns</h3>
                
                <div class="patterns-content">
                    <div class="pattern-chart">
                        <h4>Day of Week Performance</h4>
                        <div class="day-of-week-chart" id="day-of-week-chart">
                            ${this.renderDayOfWeekChart(patterns.dayOfWeek)}
                        </div>
                    </div>
                    
                    <div class="pattern-insights">
                        <h4>Key Insights</h4>
                        <ul class="insights-list">
                            ${this.generatePatternInsights(patterns).map(insight => 
                                `<li class="insight-item">${insight}</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderPredictionsSection() {
        const { predictions } = this.analytics;
        
        return `
            <div class="analytics-section predictions">
                <h3 class="section-title">Predictions & Forecasts</h3>
                
                <div class="predictions-grid">
                    <div class="prediction-card">
                        <div class="prediction-icon">📅</div>
                        <div class="prediction-value">${predictions.nextWeekAchievements}</div>
                        <div class="prediction-label">Expected achievements next week</div>
                        <div class="prediction-confidence">
                            Confidence: ${Math.round(predictions.confidenceLevel)}%
                        </div>
                    </div>
                    
                    <div class="prediction-card">
                        <div class="prediction-icon">🔥</div>
                        <div class="prediction-value">${Math.round(predictions.streakContinuationProbability)}%</div>
                        <div class="prediction-label">Streak continuation probability</div>
                        <div class="prediction-detail">
                            ${predictions.streakContinuationProbability > 70 ? 'High likelihood' : 
                              predictions.streakContinuationProbability > 40 ? 'Moderate likelihood' : 'Low likelihood'}
                        </div>
                    </div>
                    
                    ${predictions.nextMilestone ? `
                        <div class="prediction-card">
                            <div class="prediction-icon">🎯</div>
                            <div class="prediction-value">${predictions.nextMilestone.days}</div>
                            <div class="prediction-label">Days to ${predictions.nextMilestone.milestone}-day milestone</div>
                            <div class="prediction-detail">
                                ETA: ${predictions.nextMilestone.eta}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    renderComparisonsSection() {
        const { comparisons } = this.analytics;
        const changeIcon = comparisons.improvement ? '⬆️' : '⬇️';
        const changeClass = comparisons.improvement ? 'positive' : 'negative';
        
        return `
            <div class="analytics-section comparisons">
                <h3 class="section-title">Performance Comparison</h3>
                
                <div class="comparison-content">
                    <div class="comparison-chart">
                        <div class="comparison-period current">
                            <div class="period-label">Current Period</div>
                            <div class="period-value">${Math.round(comparisons.currentPeriodRate)}%</div>
                            <div class="period-detail">consistency rate</div>
                        </div>
                        
                        <div class="comparison-arrow ${changeClass}">
                            <div class="arrow-icon">${changeIcon}</div>
                            <div class="change-value">${Math.abs(comparisons.rateChange).toFixed(1)}%</div>
                        </div>
                        
                        <div class="comparison-period previous">
                            <div class="period-label">Previous Period</div>
                            <div class="period-value">${Math.round(comparisons.previousPeriodRate)}%</div>
                            <div class="period-detail">consistency rate</div>
                        </div>
                    </div>
                    
                    <div class="comparison-message ${changeClass}">
                        ${comparisons.improvement ? 
                            `🎉 Great improvement! You're ${comparisons.rateChange.toFixed(1)}% more consistent than before.` :
                            `📉 Your consistency dropped by ${Math.abs(comparisons.rateChange).toFixed(1)}%. Let's get back on track!`
                        }
                    </div>
                </div>
            </div>
        `;
    }
    
    renderDayOfWeekChart(dayOfWeekData) {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const maxValue = Math.max(...Object.values(dayOfWeekData));
        
        return days.map((day, index) => {
            const value = dayOfWeekData[index] || 0;
            const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;
            
            return `
                <div class="day-bar">
                    <div class="bar-fill" style="height: ${percentage}%"></div>
                    <div class="bar-value">${value}</div>
                    <div class="bar-label">${day}</div>
                </div>
            `;
        }).join('');
    }
    
    generatePatternInsights(patterns) {
        const insights = [];
        
        // Find best day of week
        const dayOfWeekEntries = Object.entries(patterns.dayOfWeek);
        if (dayOfWeekEntries.length > 0) {
            const bestDay = dayOfWeekEntries.reduce((a, b) => a[1] > b[1] ? a : b);
            const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            insights.push(`${dayNames[bestDay[0]]} is your most successful day with ${bestDay[1]} achievements`);
        }
        
        // Streak patterns
        if (patterns.streaks.averageLength > 0) {
            insights.push(`Your average streak length is ${patterns.streaks.averageLength.toFixed(1)} days`);
        }
        
        // Add more insights based on data
        if (patterns.monthly) {
            // Add monthly pattern insights
        }
        
        return insights;
    }
    
    renderCharts() {
        // If Chart.js is available, render more advanced charts
        if (typeof Chart !== 'undefined') {
            this.renderAdvancedCharts();
        }
    }
    
    renderAdvancedCharts() {
        // Implementation for Chart.js charts would go here
        // This is a placeholder for advanced charting functionality
    }
    
    // Helper methods for calculations
    getPeriodDays() {
        switch (this.options.period) {
            case 'last_30_days': return 30;
            case 'last_90_days': return 90;
            case 'last_year': return 365;
            default: return 90;
        }
    }
    
    calculateTrend(achievements) {
        if (achievements.length < 7) return 0;
        
        // Simple trend calculation using first and second half of period
        const midpoint = Math.floor(achievements.length / 2);
        const firstHalf = achievements.slice(0, midpoint);
        const secondHalf = achievements.slice(midpoint);
        
        const firstHalfRate = firstHalf.length / midpoint;
        const secondHalfRate = secondHalf.length / (achievements.length - midpoint);
        
        return ((secondHalfRate - firstHalfRate) / firstHalfRate) * 100;
    }
    
    calculateDayOfWeekPattern(achievements) {
        const dayOfWeekCounts = {};
        
        achievements.forEach(achievement => {
            const date = new Date(achievement.achieved_date);
            const dayOfWeek = date.getDay();
            dayOfWeekCounts[dayOfWeek] = (dayOfWeekCounts[dayOfWeek] || 0) + 1;
        });
        
        return dayOfWeekCounts;
    }
    
    calculateMonthlyPattern(achievements) {
        const monthlyData = {};
        
        achievements.forEach(achievement => {
            const date = new Date(achievement.achieved_date);
            const monthKey = `${date.getFullYear()}-${date.getMonth() + 1}`;
            monthlyData[monthKey] = (monthlyData[monthKey] || 0) + 1;
        });
        
        return monthlyData;
    }
    
    calculateStreakPatterns(achievements) {
        const streaks = this.findAllStreaks(achievements);
        const totalLength = streaks.reduce((sum, streak) => sum + streak.length, 0);
        
        return {
            count: streaks.length,
            averageLength: streaks.length > 0 ? totalLength / streaks.length : 0,
            longestStreak: streaks.length > 0 ? Math.max(...streaks.map(s => s.length)) : 0
        };
    }
    
    findAllStreaks(achievements) {
        const sortedDates = achievements
            .map(a => new Date(a.achieved_date))
            .sort((a, b) => a - b);
        
        const streaks = [];
        let currentStreak = [];
        
        for (let i = 0; i < sortedDates.length; i++) {
            const currentDate = sortedDates[i];
            const previousDate = sortedDates[i - 1];
            
            if (i === 0 || this.isConsecutiveDay(previousDate, currentDate)) {
                currentStreak.push(currentDate);
            } else {
                if (currentStreak.length > 0) {
                    streaks.push({
                        start: currentStreak[0],
                        end: currentStreak[currentStreak.length - 1],
                        length: currentStreak.length
                    });
                }
                currentStreak = [currentDate];
            }
        }
        
        // Don't forget the last streak
        if (currentStreak.length > 0) {
            streaks.push({
                start: currentStreak[0],
                end: currentStreak[currentStreak.length - 1],
                length: currentStreak.length
            });
        }
        
        return streaks;
    }
    
    findLongestStreakInPeriod(achievements) {
        const streaks = this.findAllStreaks(achievements);
        return streaks.length > 0 ? Math.max(...streaks.map(s => s.length)) : 0;
    }
    
    isConsecutiveDay(date1, date2) {
        const diffTime = Math.abs(date2 - date1);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays === 1;
    }
    
    calculateStreakContinuationProbability(achievements) {
        // Simple probability based on recent consistency
        const recentAchievements = achievements.slice(-7);
        return (recentAchievements.length / 7) * 100;
    }
    
    predictNextMilestone() {
        const currentStreak = this.streaks[0]?.current_count || 0;
        const milestones = [7, 14, 30, 50, 100, 200, 365];
        
        const nextMilestone = milestones.find(m => m > currentStreak);
        if (!nextMilestone) return null;
        
        const daysToMilestone = nextMilestone - currentStreak;
        const eta = new Date();
        eta.setDate(eta.getDate() + daysToMilestone);
        
        return {
            milestone: nextMilestone,
            days: daysToMilestone,
            eta: eta.toLocaleDateString()
        };
    }
    
    calculatePredictionConfidence(achievements) {
        // Simple confidence based on data quantity and consistency
        const dataPoints = achievements.length;
        const consistency = this.analytics.summary.consistencyRate;
        
        let confidence = Math.min(dataPoints * 2, 100); // More data = more confidence
        confidence = (confidence + consistency) / 2; // Factor in consistency
        
        return Math.max(20, Math.min(95, confidence)); // Clamp between 20-95%
    }
    
    getStreakBucket(length) {
        if (length < 7) return '1-6 days';
        if (length < 14) return '1-2 weeks';
        if (length < 30) return '2-4 weeks';
        if (length < 90) return '1-3 months';
        return '3+ months';
    }
    
    formatValue(value) {
        return value.toFixed(1);
    }
    
    setupEventListeners() {
        // Period selector
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('period-selector')) {
                this.options.period = e.target.value;
                this.loadAnalyticsData().then(() => this.render());
            }
        });
    }
    
    // Public methods
    async refresh() {
        await this.loadAnalyticsData();
        this.render();
    }
    
    setPeriod(period) {
        this.options.period = period;
        this.loadAnalyticsData().then(() => this.render());
    }
    
    setGoal(goalId) {
        this.options.goalId = goalId;
        this.loadAnalyticsData().then(() => this.render());
    }
    
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreakAnalytics;
}

// Global registration
window.StreakAnalytics = StreakAnalytics;