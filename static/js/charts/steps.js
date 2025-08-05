/**
 * Steps Bar Chart - Health Tracker
 * Interactive steps visualization optimized for 7-inch touchscreen
 */

// Steps chart configuration and utilities
window.StepsChart = {
    chart: null,
    goalLine: 10000, // Default daily goal
    
    /**
     * Initialize steps bar chart
     */
    async init(canvasId = 'steps-week-chart') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Steps chart canvas '${canvasId}' not found`);
            return null;
        }

        try {
            // Fetch steps data from API
            const data = await this.fetchStepsData();
            const ctx = canvas.getContext('2d');
            
            // Destroy existing chart if it exists
            if (this.chart) {
                this.chart.destroy();
            }

            // Create chart configuration
            const config = this.createChartConfig(data);
            
            // Initialize Chart.js
            this.chart = new Chart(ctx, config);
            
            // Update summary statistics
            this.updateStepsSummary(data);
            
            console.log('Steps chart initialized successfully');
            return this.chart;
            
        } catch (error) {
            console.error('Error initializing steps chart:', error);
            this.showError(canvas, 'Failed to load steps data');
            return null;
        }
    },

    /**
     * Fetch steps data from API
     */
    async fetchStepsData() {
        const response = await fetch('/api/charts/steps?period=week');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate data structure
        if (!data.labels || !data.values) {
            throw new Error('Invalid chart data structure');
        }
        
        return data;
    },

    /**
     * Create Chart.js configuration for steps bar chart
     */
    createChartConfig(data) {
        return {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Daily Steps',
                        data: data.values,
                        backgroundColor: this.createStepsGradient(),
                        borderColor: ChartColors.steps.primary,
                        borderWidth: 2,
                        borderRadius: 6,
                        borderSkipped: false,
                        // Color bars based on goal achievement
                        backgroundColor: data.values.map(value => 
                            value >= this.goalLine 
                                ? ChartColors.steps.primary 
                                : 'rgba(102, 126, 234, 0.6)'
                        ),
                        // Add custom properties for tooltips
                        goalAchieved: data.values.map(value => value >= this.goalLine)
                    },
                    {
                        label: 'Daily Goal',
                        data: Array(data.labels.length).fill(this.goalLine),
                        type: 'line',
                        borderColor: ChartColors.goal,
                        backgroundColor: 'transparent',
                        borderWidth: 3,
                        borderDash: [8, 4],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        tension: 0,
                        order: 0 // Draw goal line on top
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false // Hide legend for cleaner look
                    },
                    tooltip: {
                        ...Chart.defaults.plugins.tooltip,
                        callbacks: {
                            title: (context) => {
                                return `${context[0].label}`;
                            },
                            label: (context) => {
                                if (context.datasetIndex === 0) {
                                    const value = context.parsed.y;
                                    const goal = this.goalLine;
                                    const percentage = ((value / goal) * 100).toFixed(0);
                                    const status = value >= goal ? '🎯 Goal achieved!' : `${goal - value} steps to goal`;
                                    
                                    return [
                                        `Steps: ${value.toLocaleString()}`,
                                        `Goal: ${percentage}% (${status})`
                                    ];
                                } else {
                                    return `Daily Goal: ${context.parsed.y.toLocaleString()} steps`;
                                }
                            }
                        },
                        filter: (tooltipItem) => {
                            // Only show tooltip for steps bars, not goal line
                            return tooltipItem.datasetIndex === 0;
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 12,
                                weight: '500'
                            },
                            color: '#64748b'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: Math.max(...data.values, this.goalLine) * 1.1, // 10% padding above max
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            color: '#64748b',
                            callback: function(value) {
                                if (value >= 1000) {
                                    return (value / 1000).toFixed(0) + 'k';
                                }
                                return value.toLocaleString();
                            }
                        }
                    }
                },
                elements: {
                    bar: {
                        borderRadius: 6
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutCubic'
                },
                // Touch-friendly options
                onHover: (event, elements, chart) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements, chart) => {
                    if (elements.length > 0) {
                        const element = elements[0];
                        const dataIndex = element.index;
                        const value = data.values[dataIndex];
                        const label = data.labels[dataIndex];
                        
                        // Provide haptic feedback
                        if (window.HealthTrackerUtils && window.HealthTrackerUtils.hapticFeedback) {
                            window.HealthTrackerUtils.hapticFeedback('light');
                        }
                        
                        // Could trigger detailed view or action
                        console.log(`Clicked on ${label}: ${value.toLocaleString()} steps`);
                    }
                }
            }
        };
    },

    /**
     * Create gradient background for steps bars
     */
    createStepsGradient() {
        // This will be called by Chart.js with canvas context
        return function(context) {
            const chart = context.chart;
            const {ctx, chartArea} = chart;
            
            if (!chartArea) {
                return null;
            }
            
            const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
            gradient.addColorStop(0, ChartColors.steps.gradient[1]);
            gradient.addColorStop(1, ChartColors.steps.gradient[0]);
            return gradient;
        };
    },

    /**
     * Update steps summary statistics
     */
    updateStepsSummary(data) {
        try {
            // Calculate statistics
            const totalSteps = data.values.reduce((sum, value) => sum + value, 0);
            const avgSteps = Math.round(totalSteps / data.values.length);
            const goalDays = data.values.filter(value => value >= this.goalLine).length;
            const maxSteps = Math.max(...data.values);
            const maxDay = data.labels[data.values.indexOf(maxSteps)];
            
            // Update week summary header if it exists
            const totalElement = document.getElementById('week-steps-total');
            if (totalElement) {
                totalElement.textContent = totalSteps.toLocaleString();
            }
            
            // Update active days if element exists
            const activeDaysElement = document.getElementById('week-active-days');
            if (activeDaysElement) {
                activeDaysElement.textContent = `${goalDays}/7`;
            }
            
            // Update chart footer with insights
            this.updateChartFooter({
                totalSteps,
                avgSteps,
                goalDays,
                maxSteps,
                maxDay,
                trend: data.trend
            });
            
        } catch (error) {
            console.error('Error updating steps summary:', error);
        }
    },

    /**
     * Update chart footer with insights
     */
    updateChartFooter(stats) {
        const footerElement = document.querySelector('#steps-week-chart').closest('.chart-container')?.querySelector('.chart-footer');
        if (!footerElement) return;
        
        let insights = [];
        
        if (stats.goalDays === 7) {
            insights.push('🎉 Perfect week - all goals achieved!');
        } else if (stats.goalDays >= 5) {
            insights.push(`🎯 Great consistency - ${stats.goalDays}/7 goal days`);
        } else if (stats.goalDays >= 3) {
            insights.push(`📈 ${stats.goalDays}/7 goal days - keep building momentum`);
        } else {
            insights.push(`🚀 ${7 - stats.goalDays} more days to reach weekly target`);
        }
        
        if (stats.maxSteps >= 15000) {
            insights.push(`💪 Peak day: ${stats.maxSteps.toLocaleString()} steps on ${stats.maxDay}`);
        }
        
        // Create footer content
        footerElement.innerHTML = `
            <div class="chart-goal-line">
                <span class="goal-indicator"></span>
                <span class="goal-text">Goal: ${this.goalLine.toLocaleString()} steps/day</span>
            </div>
            <div class="chart-insights">
                <div class="insight-text">${insights[0] || 'Keep moving towards your goals!'}</div>
                ${insights[1] ? `<div class="insight-text secondary">${insights[1]}</div>` : ''}
            </div>
        `;
    },

    /**
     * Update chart with new data
     */
    async refresh() {
        if (!this.chart) {
            console.warn('Steps chart not initialized');
            return;
        }
        
        try {
            const data = await this.fetchStepsData();
            
            // Update chart data
            this.chart.data.labels = data.labels;
            this.chart.data.datasets[0].data = data.values;
            this.chart.data.datasets[0].backgroundColor = data.values.map(value => 
                value >= this.goalLine 
                    ? ChartColors.steps.primary 
                    : 'rgba(102, 126, 234, 0.6)'
            );
            
            // Update and animate
            this.chart.update('active');
            
            // Update summary
            this.updateStepsSummary(data);
            
            console.log('Steps chart refreshed');
            
        } catch (error) {
            console.error('Error refreshing steps chart:', error);
        }
    },

    /**
     * Show error message in chart container
     */
    showError(canvas, message) {
        const container = canvas.closest('.chart-body');
        if (container) {
            container.innerHTML = `
                <div class="chart-error">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">📊</div>
                    <div style="font-size: 0.875rem; color: #ef4444;">${message}</div>
                    <button onclick="window.StepsChart.init()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 0.375rem; cursor: pointer;">
                        Retry
                    </button>
                </div>
            `;
        }
    },

    /**
     * Destroy chart instance
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
};

// Auto-initialize when DOM is ready and canvas exists
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure chart infrastructure is loaded
    setTimeout(() => {
        if (document.getElementById('steps-week-chart')) {
            window.StepsChart.init();
        }
    }, 200);
});

// Export for global access
window.StepsChart = window.StepsChart;

// Integration with main charts system
if (window.WeekCharts) {
    window.WeekCharts.steps = window.StepsChart;
}

console.log('Steps chart module loaded');