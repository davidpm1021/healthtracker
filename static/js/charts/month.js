/**
 * Month Charts System - Health Tracker
 * Centralized month-view chart management with period navigation
 */

// Month charts configuration and utilities
window.MonthCharts = {
    charts: {},
    currentPeriod: null,
    
    /**
     * Initialize all month charts
     */
    async initAll() {
        console.log('Initializing month charts system...');
        
        this.currentPeriod = this.getCurrentPeriod();
        
        // Initialize individual charts
        await this.initStepsChart();
        await this.initSleepChart();
        await this.initWeightChart();
        await this.initHeartRateChart();
        
        console.log('Month charts system initialized');
    },
    
    /**
     * Get current period information
     */
    getCurrentPeriod() {
        const now = new Date();
        return {
            year: now.getFullYear(),
            month: now.getMonth() + 1,
            monthName: now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
            offset: 0
        };
    },
    
    /**
     * Initialize steps month chart (area chart)
     */
    async initStepsChart() {
        const canvas = document.getElementById('steps-month-chart');
        if (!canvas) {
            console.warn('Steps month chart canvas not found');
            return;
        }
        
        try {
            const data = await this.fetchChartData('steps', 'month');
            const ctx = canvas.getContext('2d');
            
            if (this.charts.steps) {
                this.charts.steps.destroy();
            }
            
            this.charts.steps = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Daily Steps',
                            data: data.values,
                            borderColor: ChartColors.steps.primary,
                            backgroundColor: ChartColors.steps.background,
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#ffffff',
                            pointBorderColor: ChartColors.steps.primary,
                            pointBorderWidth: 2,
                        },
                        {
                            label: 'Daily Goal',
                            data: Array(data.labels.length).fill(10000),
                            borderColor: ChartColors.goal,
                            backgroundColor: 'transparent',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0,
                            pointHoverRadius: 0,
                        }
                    ]
                },
                options: {
                    ...this.getBaseMonthChartOptions(),
                    scales: {
                        x: {
                            ...this.getBaseXScale(),
                            ticks: {
                                maxTicksLimit: 8,
                                font: { size: 10 },
                                color: '#64748b'
                            }
                        },
                        y: {
                            ...this.getBaseYScale(),
                            ticks: {
                                callback: function(value) {
                                    return value >= 1000 ? (value / 1000).toFixed(0) + 'k' : value.toString();
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    if (context.datasetIndex === 0) {
                                        const steps = context.parsed.y;
                                        const goalProgress = ((steps / 10000) * 100).toFixed(0);
                                        return [
                                            `Steps: ${steps.toLocaleString()}`,
                                            `Goal: ${goalProgress}%`
                                        ];
                                    }
                                    return null;
                                },
                                filter: (tooltipItem) => tooltipItem.datasetIndex === 0
                            }
                        }
                    }
                }
            });
            
            this.updateInsight('steps', data);
            console.log('Steps month chart initialized');
            
        } catch (error) {
            console.error('Error initializing steps month chart:', error);
            this.showChartError(canvas, 'Failed to load monthly steps data');
        }
    },
    
    /**
     * Initialize sleep month chart
     */
    async initSleepChart() {
        const canvas = document.getElementById('sleep-month-chart');
        if (!canvas) {
            console.warn('Sleep month chart canvas not found');
            return;
        }
        
        try {
            const data = await this.fetchChartData('sleep', 'month');
            const ctx = canvas.getContext('2d');
            
            if (this.charts.sleep) {
                this.charts.sleep.destroy();
            }
            
            this.charts.sleep = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Sleep Duration',
                            data: data.values.map(v => v / 60), // Convert to hours
                            borderColor: ChartColors.sleep.primary,
                            backgroundColor: ChartColors.sleep.background,
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#ffffff',
                            pointBorderColor: ChartColors.sleep.primary,
                            pointBorderWidth: 2,
                        },
                        {
                            label: 'Sleep Goal',
                            data: Array(data.labels.length).fill(8),
                            borderColor: ChartColors.goal,
                            backgroundColor: 'transparent',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0,
                            pointHoverRadius: 0,
                        }
                    ]
                },
                options: {
                    ...this.getBaseMonthChartOptions(),
                    scales: {
                        x: this.getBaseXScale(),
                        y: {
                            ...this.getBaseYScale(),
                            max: 12,
                            ticks: {
                                callback: function(value) {
                                    return value + 'h';
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    if (context.datasetIndex === 0) {
                                        return `Sleep: ${context.parsed.y.toFixed(1)}h`;
                                    }
                                    return null;
                                },
                                filter: (tooltipItem) => tooltipItem.datasetIndex === 0
                            }
                        }
                    }
                }
            });
            
            this.updateInsight('sleep', data);
            console.log('Sleep month chart initialized');
            
        } catch (error) {
            console.error('Error initializing sleep month chart:', error);
            this.showChartError(canvas, 'Failed to load monthly sleep data');
        }
    },
    
    /**
     * Initialize weight month chart
     */
    async initWeightChart() {
        const canvas = document.getElementById('weight-month-chart');
        if (!canvas) {
            console.warn('Weight month chart canvas not found');
            return;
        }
        
        try {
            const data = await this.fetchChartData('weight', 'month');
            const ctx = canvas.getContext('2d');
            
            if (this.charts.weight) {
                this.charts.weight.destroy();
            }
            
            // Filter out zero values for clean visualization
            const cleanValues = data.values.map(v => v === 0 ? null : v);
            
            this.charts.weight = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Weight',
                            data: cleanValues,
                            borderColor: ChartColors.weight.primary,
                            backgroundColor: ChartColors.weight.background,
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#ffffff',
                            pointBorderColor: ChartColors.weight.primary,
                            pointBorderWidth: 2,
                            spanGaps: true
                        }
                    ]
                },
                options: {
                    ...this.getBaseMonthChartOptions(),
                    scales: {
                        x: this.getBaseXScale(),
                        y: {
                            ...this.getBaseYScale(),
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(1) + ' kg';
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const value = context.parsed.y;
                                    return value !== null ? `Weight: ${value.toFixed(1)} kg` : null;
                                },
                                filter: (tooltipItem) => tooltipItem.parsed.y !== null
                            }
                        }
                    }
                }
            });
            
            this.updateInsight('weight', data);
            console.log('Weight month chart initialized');
            
        } catch (error) {
            console.error('Error initializing weight month chart:', error);
            this.showChartError(canvas, 'Failed to load monthly weight data');
        }
    },
    
    /**
     * Initialize heart rate month chart
     */
    async initHeartRateChart() {
        const canvas = document.getElementById('heart-rate-month-chart');
        if (!canvas) {
            console.warn('Heart rate month chart canvas not found');
            return;
        }
        
        try {
            const data = await this.fetchChartData('heart_rate', 'month');
            const ctx = canvas.getContext('2d');
            
            if (this.charts.heartRate) {
                this.charts.heartRate.destroy();
            }
            
            this.charts.heartRate = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Heart Rate',
                            data: data.values,
                            borderColor: ChartColors.heartRate.primary,
                            backgroundColor: ChartColors.heartRate.background,
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#ffffff',
                            pointBorderColor: ChartColors.heartRate.primary,
                            pointBorderWidth: 2,
                        }
                    ]
                },
                options: {
                    ...this.getBaseMonthChartOptions(),
                    scales: {
                        x: this.getBaseXScale(),
                        y: {
                            ...this.getBaseYScale(),
                            beginAtZero: false,
                            min: 50,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + ' bpm';
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return `Heart Rate: ${context.parsed.y} bpm`;
                                }
                            }
                        }
                    }
                }
            });
            
            this.updateInsight('heart_rate', data);
            console.log('Heart rate month chart initialized');
            
        } catch (error) {
            console.error('Error initializing heart rate month chart:', error);
            this.showChartError(canvas, 'Failed to load monthly heart rate data');
        }
    },
    
    /**
     * Fetch chart data from API
     */
    async fetchChartData(metric, period) {
        try {
            const response = await fetch(`/api/charts/${metric}?period=${period}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${metric} month chart data:`, error);
            throw error;
        }
    },
    
    /**
     * Get base chart options for month charts
     */
    getBaseMonthChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            elements: {
                point: {
                    hoverBorderWidth: 3
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            animation: {
                duration: 800,
                easing: 'easeOutCubic'
            }
        };
    },
    
    /**
     * Get base X scale configuration
     */
    getBaseXScale() {
        return {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    size: 10,
                    weight: '500'
                },
                color: '#64748b',
                maxTicksLimit: 10
            }
        };
    },
    
    /**
     * Get base Y scale configuration
     */
    getBaseYScale() {
        return {
            beginAtZero: true,
            grid: {
                color: 'rgba(148, 163, 184, 0.1)',
                drawBorder: false
            },
            ticks: {
                font: {
                    size: 10
                },
                color: '#64748b'
            }
        };
    },
    
    /**
     * Update chart insight text
     */
    updateInsight(metric, data) {
        const insightElement = document.getElementById(`${metric}-month-insight`);
        if (!insightElement) return;
        
        try {
            let insightText = '';
            const validValues = data.values.filter(v => v && v > 0);
            
            switch (metric) {
                case 'steps':
                    const totalSteps = validValues.reduce((sum, v) => sum + v, 0);
                    const avgSteps = Math.round(totalSteps / validValues.length);
                    const goalDays = validValues.filter(v => v >= 10000).length;
                    insightText = `${totalSteps.toLocaleString()} total steps • ${avgSteps.toLocaleString()} daily avg • ${goalDays}/${validValues.length} goal days`;
                    break;
                    
                case 'sleep':
                    const avgSleep = validValues.reduce((sum, v) => sum + v, 0) / validValues.length / 60;
                    const targetNights = validValues.filter(v => v >= 480).length; // 8+ hours
                    insightText = `${avgSleep.toFixed(1)}h average sleep • ${targetNights}/${validValues.length} nights met 8h target`;
                    break;
                    
                case 'weight':
                    if (validValues.length >= 2) {
                        const weightChange = validValues[validValues.length - 1] - validValues[0];
                        const trend = weightChange > 0.5 ? '↗' : weightChange < -0.5 ? '↘' : '→';
                        insightText = `${trend} ${Math.abs(weightChange).toFixed(1)}kg change • ${validValues.length} measurements this month`;
                    } else {
                        insightText = `${validValues.length} weight measurements recorded`;
                    }
                    break;
                    
                case 'heart_rate':
                    const avgHR = Math.round(validValues.reduce((sum, v) => sum + v, 0) / validValues.length);
                    const healthyCount = validValues.filter(v => v >= 60 && v <= 80).length;
                    insightText = `${avgHR} bpm average • ${healthyCount}/${validValues.length} readings in healthy range`;
                    break;
            }
            
            const textElement = insightElement.querySelector('.insight-text');
            if (textElement) {
                textElement.textContent = insightText;
            }
            
        } catch (error) {
            console.error(`Error updating ${metric} insight:`, error);
        }
    },
    
    /**
     * Refresh all charts
     */
    async refreshAll() {
        console.log('Refreshing all month charts...');
        
        await this.initStepsChart();
        await this.initSleepChart();
        await this.initWeightChart();
        await this.initHeartRateChart();
        
        console.log('All month charts refreshed');
    },
    
    /**
     * Refresh specific chart
     */
    async refreshChart(metric) {
        console.log(`Refreshing ${metric} month chart...`);
        
        switch (metric) {
            case 'steps':
                await this.initStepsChart();
                break;
            case 'sleep':
                await this.initSleepChart();
                break;
            case 'weight':
                await this.initWeightChart();
                break;
            case 'heart_rate':
                await this.initHeartRateChart();
                break;
            default:
                console.warn(`Unknown chart metric: ${metric}`);
        }
    },
    
    /**
     * Show error message in chart container
     */
    showChartError(canvas, message) {
        const container = canvas.closest('.chart-body');
        if (container) {
            container.innerHTML = `
                <div class="chart-error">
                    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📊</div>
                    <div style="font-size: 0.875rem; color: #ef4444;">${message}</div>
                </div>
            `;
        }
    },
    
    /**
     * Destroy all charts
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
};

// Global functions for month view integration
window.initializeStepsMonthChart = () => window.MonthCharts.initStepsChart();
window.initializeSleepMonthChart = () => window.MonthCharts.initSleepChart();
window.initializeWeightMonthChart = () => window.MonthCharts.initWeightChart();
window.initializeHeartRateMonthChart = () => window.MonthCharts.initHeartRateChart();

window.refreshMonthChart = (metric) => window.MonthCharts.refreshChart(metric);

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Delay to ensure other components load first
    setTimeout(() => {
        if (document.getElementById('steps-month-chart')) {
            window.MonthCharts.initAll();
        }
    }, 600);
});

// Export for global access
window.MonthCharts = window.MonthCharts;

console.log('Month charts system loaded');