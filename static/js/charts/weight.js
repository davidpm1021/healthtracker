/**
 * Weight Line Chart - Health Tracker
 * Interactive weight visualization with moving averages, optimized for 7-inch touchscreen
 */

// Weight chart configuration and utilities
window.WeightChart = {
    chart: null,
    targetWeight: null, // Can be set based on user goals
    
    /**
     * Initialize weight line chart
     */
    async init(canvasId = 'weight-week-chart') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Weight chart canvas '${canvasId}' not found`);
            return null;
        }

        try {
            // Fetch weight data from API
            const data = await this.fetchWeightData();
            const ctx = canvas.getContext('2d');
            
            // Destroy existing chart if it exists
            if (this.chart) {
                this.chart.destroy();
            }

            // Create chart configuration
            const config = this.createChartConfig(data);
            
            // Initialize Chart.js
            this.chart = new Chart(ctx, config);
            
            // Update trend summary
            this.updateWeightTrendSummary(data);
            
            console.log('Weight chart initialized successfully');
            return this.chart;
            
        } catch (error) {
            console.error('Error initializing weight chart:', error);
            this.showError(canvas, 'Failed to load weight data');
            return null;
        }
    },

    /**
     * Fetch weight data from API
     */
    async fetchWeightData() {
        const response = await fetch('/api/charts/weight?period=week');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate data structure
        if (!data.labels || !data.values) {
            throw new Error('Invalid weight chart data structure');
        }
        
        return data;
    },

    /**
     * Create Chart.js configuration for weight line chart
     */
    createChartConfig(data) {
        // Filter out zero values for clean visualization
        const cleanData = this.prepareWeightData(data);
        
        return {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Weight',
                        data: cleanData.actualValues,
                        borderColor: ChartColors.weight.primary,
                        backgroundColor: ChartColors.weight.background,
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#ffffff',
                        pointBorderColor: ChartColors.weight.primary,
                        pointBorderWidth: 2,
                        // Custom point styling for measurements vs. gaps
                        pointRadius: cleanData.actualValues.map(v => v === null ? 0 : 6),
                        pointHoverRadius: cleanData.actualValues.map(v => v === null ? 0 : 8),
                        spanGaps: true // Connect across null values
                    },
                    {
                        label: '3-Day Average',
                        data: cleanData.movingAverage,
                        borderColor: ChartColors.average,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: ChartColors.average,
                        pointBorderColor: ChartColors.average,
                        pointBorderWidth: 1,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false // Clean look for 7-inch screen
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
                                    if (value === null) return null;
                                    
                                    const trend = this.calculateDayTrend(data.values, context.dataIndex);
                                    const trendText = trend > 0 ? '↗️' : trend < 0 ? '↘️' : '→';
                                    
                                    return [
                                        `Weight: ${value.toFixed(1)} kg`,
                                        `Trend: ${trendText} ${trend !== 0 ? Math.abs(trend).toFixed(1) + 'kg' : 'stable'}`
                                    ];
                                } else {
                                    const value = context.parsed.y;
                                    return value !== null ? `3-day avg: ${value.toFixed(1)} kg` : null;
                                }
                            },
                            filter: (tooltipItem) => {
                                return tooltipItem.parsed.y !== null;
                            }
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
                        beginAtZero: false,
                        min: this.calculateWeightRange(cleanData.actualValues).min,
                        max: this.calculateWeightRange(cleanData.actualValues).max,
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
                                return value.toFixed(1) + ' kg';
                            }
                        }
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
                },
                // Touch-friendly options
                onHover: (event, elements, chart) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements, chart) => {
                    if (elements.length > 0) {
                        const element = elements[0];
                        const dataIndex = element.index;
                        const value = cleanData.actualValues[dataIndex];
                        const label = data.labels[dataIndex];
                        
                        if (value !== null) {
                            // Provide haptic feedback
                            if (window.HealthTrackerUtils && window.HealthTrackerUtils.hapticFeedback) {
                                window.HealthTrackerUtils.hapticFeedback('light');
                            }
                            
                            console.log(`Clicked on ${label}: ${value.toFixed(1)} kg`);
                        }
                    }
                }
            }
        };
    },

    /**
     * Prepare weight data for visualization (handle gaps and moving averages)
     */
    prepareWeightData(data) {
        // Convert 0 values to null for proper gap handling
        const actualValues = data.values.map(v => v === 0 ? null : v);
        
        // Calculate simple 3-day moving average (only for actual measurements)
        const movingAverage = [];
        
        for (let i = 0; i < actualValues.length; i++) {
            if (actualValues[i] === null) {
                movingAverage.push(null);
                continue;
            }
            
            // Look for nearby values to average
            const window = [];
            for (let j = Math.max(0, i - 1); j <= Math.min(actualValues.length - 1, i + 1); j++) {
                if (actualValues[j] !== null) {
                    window.push(actualValues[j]);
                }
            }
            
            if (window.length > 0) {
                movingAverage.push(window.reduce((sum, val) => sum + val, 0) / window.length);
            } else {
                movingAverage.push(null);
            }
        }
        
        return {
            actualValues,
            movingAverage
        };
    },

    /**
     * Calculate appropriate weight range for Y-axis
     */
    calculateWeightRange(values) {
        const validValues = values.filter(v => v !== null);
        if (validValues.length === 0) {
            return { min: 60, max: 90 }; // Default range
        }
        
        const min = Math.min(...validValues);
        const max = Math.max(...validValues);
        const range = max - min;
        const padding = Math.max(1, range * 0.1); // 10% padding, minimum 1kg
        
        return {
            min: Math.max(0, min - padding),
            max: max + padding
        };
    },

    /**
     * Calculate day-to-day trend for tooltip
     */
    calculateDayTrend(values, index) {
        if (index === 0 || values[index] === 0) return 0;
        
        // Find previous non-zero value
        for (let i = index - 1; i >= 0; i--) {
            if (values[i] !== 0) {
                return values[index] - values[i];
            }
        }
        return 0;
    },

    /**
     * Update weight trend summary
     */
    updateWeightTrendSummary(data) {
        const summaryElement = document.getElementById('weight-trend-summary');
        if (!summaryElement) return;

        try {
            const validValues = data.values.filter(v => v > 0);
            const trend = data.trend || 'stable';
            
            let trendConfig = {
                stable: { arrow: '→', text: 'Stable this week', class: 'trend-flat' },
                up: { arrow: '↗', text: 'Increasing this week', class: 'trend-up' },
                down: { arrow: '↘', text: 'Decreasing this week', class: 'trend-down' }
            };
            
            const config = trendConfig[trend] || trendConfig.stable;
            
            // Add measurement frequency info
            const measurementDays = validValues.length;
            const frequencyText = measurementDays >= 5 ? 'Great tracking!' : 
                                 measurementDays >= 3 ? 'Good consistency' : 
                                 'Try daily weigh-ins';
            
            summaryElement.innerHTML = `
                <span class="trend-arrow ${config.class}">${config.arrow}</span>
                <span class="trend-text">${config.text}</span>
                <span class="trend-frequency">(${measurementDays} measurements - ${frequencyText})</span>
            `;
            
        } catch (error) {
            console.error('Error updating weight trend summary:', error);
        }
    },

    /**
     * Update chart with new data
     */
    async refresh() {
        if (!this.chart) {
            console.warn('Weight chart not initialized');
            return;
        }
        
        try {
            const data = await this.fetchWeightData();
            const cleanData = this.prepareWeightData(data);
            
            // Update chart data
            this.chart.data.labels = data.labels;
            this.chart.data.datasets[0].data = cleanData.actualValues;
            this.chart.data.datasets[1].data = cleanData.movingAverage;
            
            // Update Y-axis range
            const range = this.calculateWeightRange(cleanData.actualValues);
            this.chart.options.scales.y.min = range.min;
            this.chart.options.scales.y.max = range.max;
            
            // Update and animate
            this.chart.update('active');
            
            // Update trend summary
            this.updateWeightTrendSummary(data);
            
            console.log('Weight chart refreshed');
            
        } catch (error) {
            console.error('Error refreshing weight chart:', error);
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
                    <div style="font-size: 2rem; margin-bottom: 1rem;">⚖️</div>
                    <div style="font-size: 0.875rem; color: #ef4444;">${message}</div>
                    <button onclick="window.WeightChart.init()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #10b981; color: white; border: none; border-radius: 0.375rem; cursor: pointer;">
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
    setTimeout(() => {
        if (document.getElementById('weight-week-chart')) {
            window.WeightChart.init();
        }
    }, 300);
});

// Export for global access
window.WeightChart = window.WeightChart;

// Integration with main charts system
if (window.WeekCharts) {
    window.WeekCharts.weight = window.WeightChart;
}

console.log('Weight chart module loaded');