/**
 * Heart Rate Line Chart - Health Tracker
 * Interactive heart rate visualization with trend indicators, optimized for 7-inch touchscreen
 */

// Heart rate chart configuration and utilities
window.HeartRateChart = {
    chart: null,
    restingHRTarget: { min: 60, max: 80 }, // Healthy resting HR range
    
    /**
     * Initialize heart rate line chart
     */
    async init(canvasId = 'heart-rate-week-chart') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Heart rate chart canvas '${canvasId}' not found`);
            return null;
        }

        try {
            // Fetch heart rate data from API
            const data = await this.fetchHeartRateData();
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
            this.updateHeartRateTrendSummary(data);
            
            console.log('Heart rate chart initialized successfully');
            return this.chart;
            
        } catch (error) {
            console.error('Error initializing heart rate chart:', error);
            this.showError(canvas, 'Failed to load heart rate data');
            return null;
        }
    },

    /**
     * Fetch heart rate data from API
     */
    async fetchHeartRateData() {
        const response = await fetch('/api/charts/heart_rate?period=week');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate data structure
        if (!data.labels || !data.values) {
            throw new Error('Invalid heart rate chart data structure');
        }
        
        return data;
    },

    /**
     * Create Chart.js configuration for heart rate line chart
     */
    createChartConfig(data) {
        return {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Heart Rate',
                        data: data.values,
                        borderColor: ChartColors.heartRate.primary,
                        backgroundColor: ChartColors.heartRate.background,
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#ffffff',
                        pointBorderColor: ChartColors.heartRate.primary,
                        pointBorderWidth: 2,
                        // Color points based on healthy range
                        pointBackgroundColor: data.values.map(hr => 
                            this.isHealthyHeartRate(hr) ? '#ffffff' : '#ffeb3b'
                        ),
                        pointBorderColor: data.values.map(hr => 
                            this.isHealthyHeartRate(hr) ? ChartColors.heartRate.primary : '#ff9800'
                        )
                    },
                    // Healthy range reference bands
                    {
                        label: 'Healthy Range (Upper)',
                        data: Array(data.labels.length).fill(this.restingHRTarget.max),
                        borderColor: 'rgba(34, 197, 94, 0.3)',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        tension: 0
                    },
                    {
                        label: 'Healthy Range (Lower)',
                        data: Array(data.labels.length).fill(this.restingHRTarget.min),
                        borderColor: 'rgba(34, 197, 94, 0.3)',
                        backgroundColor: 'rgba(34, 197, 94, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        fill: '+1', // Fill between this and previous dataset
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        tension: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        ...Chart.defaults.plugins.tooltip,
                        callbacks: {
                            title: (context) => {
                                return `${context[0].label}`;
                            },
                            label: (context) => {
                                if (context.datasetIndex === 0) {
                                    const hr = context.parsed.y;
                                    const status = this.getHeartRateStatus(hr);
                                    const trend = this.calculateHRTrend(data.values, context.dataIndex);
                                    
                                    return [
                                        `Heart Rate: ${hr} bpm`,
                                        `Status: ${status.text}`,
                                        trend ? `Trend: ${trend}` : ''
                                    ].filter(Boolean);
                                }
                                return null; // Don't show tooltips for reference lines
                            },
                            filter: (tooltipItem) => {
                                return tooltipItem.datasetIndex === 0;
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
                        min: Math.max(45, Math.min(...data.values) - 5),
                        max: Math.min(110, Math.max(...data.values) + 5),
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
                                return value + ' bpm';
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
                        const hr = data.values[dataIndex];
                        const label = data.labels[dataIndex];
                        
                        // Provide haptic feedback
                        if (window.HealthTrackerUtils && window.HealthTrackerUtils.hapticFeedback) {
                            window.HealthTrackerUtils.hapticFeedback('light');
                        }
                        
                        console.log(`Clicked on ${label}: ${hr} bpm`);
                    }
                }
            }
        };
    },

    /**
     * Check if heart rate is in healthy resting range
     */
    isHealthyHeartRate(hr) {
        return hr >= this.restingHRTarget.min && hr <= this.restingHRTarget.max;
    },

    /**
     * Get heart rate status with emoji and description
     */
    getHeartRateStatus(hr) {
        if (hr < 50) return { emoji: '🔽', text: 'Very Low (Bradycardia risk)' };
        if (hr < 60) return { emoji: '💪', text: 'Low (Athletic)' };
        if (hr <= 80) return { emoji: '✅', text: 'Healthy Range' };
        if (hr <= 100) return { emoji: '📈', text: 'Elevated' };
        return { emoji: '⚠️', text: 'High (Tachycardia risk)' };
    },

    /**
     * Calculate heart rate trend between measurements
     */
    calculateHRTrend(values, index) {
        if (index === 0) return null;
        
        const current = values[index];
        const previous = values[index - 1];
        const diff = current - previous;
        
        if (Math.abs(diff) <= 2) return '→ Stable';
        return diff > 0 ? `↗ +${diff} bpm` : `↘ ${diff} bpm`;
    },

    /**
     * Update heart rate trend summary
     */
    updateHeartRateTrendSummary(data) {
        const summaryElement = document.getElementById('heart-rate-trend-summary');
        if (!summaryElement) return;

        try {
            const avgHR = Math.round(data.values.reduce((sum, hr) => sum + hr, 0) / data.values.length);
            const healthyCount = data.values.filter(hr => this.isHealthyHeartRate(hr)).length;
            const trend = data.trend || 'stable';
            
            // Get trend configuration
            const trendConfig = {
                stable: { arrow: '→', text: 'Stable patterns', class: 'trend-flat' },
                up: { arrow: '↗', text: 'Trending higher', class: 'trend-up' },
                down: { arrow: '↘', text: 'Improving', class: 'trend-down' }
            };
            
            const config = trendConfig[trend] || trendConfig.stable;
            const status = this.getHeartRateStatus(avgHR);
            
            summaryElement.innerHTML = `
                <span class="trend-arrow ${config.class}">${config.arrow}</span>
                <span class="trend-text">${config.text}</span>
                <span class="hr-status">(Avg: ${avgHR} bpm ${status.emoji})</span>
            `;
            
        } catch (error) {
            console.error('Error updating heart rate trend summary:', error);
        }
    },

    /**
     * Update chart with new data
     */
    async refresh() {
        if (!this.chart) {
            console.warn('Heart rate chart not initialized');
            return;
        }
        
        try {
            const data = await this.fetchHeartRateData();
            
            // Update chart data
            this.chart.data.labels = data.labels;
            this.chart.data.datasets[0].data = data.values;
            
            // Update point colors based on healthy range
            this.chart.data.datasets[0].pointBackgroundColor = data.values.map(hr => 
                this.isHealthyHeartRate(hr) ? '#ffffff' : '#ffeb3b'
            );
            this.chart.data.datasets[0].pointBorderColor = data.values.map(hr => 
                this.isHealthyHeartRate(hr) ? ChartColors.heartRate.primary : '#ff9800'
            );
            
            // Update Y-axis range
            this.chart.options.scales.y.min = Math.max(45, Math.min(...data.values) - 5);
            this.chart.options.scales.y.max = Math.min(110, Math.max(...data.values) + 5);
            
            // Update and animate
            this.chart.update('active');
            
            // Update trend summary
            this.updateHeartRateTrendSummary(data);
            
            console.log('Heart rate chart refreshed');
            
        } catch (error) {
            console.error('Error refreshing heart rate chart:', error);
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
                    <div style="font-size: 2rem; margin-bottom: 1rem;">❤️</div>
                    <div style="font-size: 0.875rem; color: #ef4444;">${message}</div>
                    <button onclick="window.HeartRateChart.init()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #e74c3c; color: white; border: none; border-radius: 0.375rem; cursor: pointer;">
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
        if (document.getElementById('heart-rate-week-chart')) {
            window.HeartRateChart.init();
        }
    }, 400);
});

// Export for global access
window.HeartRateChart = window.HeartRateChart;

// Integration with main charts system
if (window.WeekCharts) {
    window.WeekCharts.heartRate = window.HeartRateChart;
}

console.log('Heart rate chart module loaded');