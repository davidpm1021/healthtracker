/**
 * Chart.js configuration and utilities for Health Tracker dashboard
 * Optimized for 7-inch touchscreen interface
 */

// Global chart instances storage
window.WeekCharts = {};

// Chart.js global configuration for 7-inch touchscreen
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#64748b';
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// Touch-friendly interaction settings
Chart.defaults.interaction = {
    mode: 'nearest',
    intersect: false,
};

Chart.defaults.plugins.tooltip = {
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    titleColor: '#f8fafc',
    bodyColor: '#f8fafc',
    borderColor: '#334155',
    borderWidth: 1,
    cornerRadius: 8,
    displayColors: false,
    padding: 12,
    titleFont: {
        size: 14,
        weight: '600'
    },
    bodyFont: {
        size: 13
    }
};

// Color palette optimized for health dashboard
const ChartColors = {
    steps: {
        primary: '#667eea',
        secondary: '#764ba2',
        background: 'rgba(102, 126, 234, 0.1)',
        gradient: ['#667eea', '#764ba2']
    },
    sleep: {
        primary: '#764ba2',
        secondary: '#5d3a7b',
        background: 'rgba(118, 75, 162, 0.1)',
        gradient: ['#764ba2', '#667eea']
    },
    weight: {
        primary: '#42b883',
        secondary: '#369870',
        background: 'rgba(66, 184, 131, 0.1)',
        gradient: ['#42b883', '#2dd4bf']
    },
    heartRate: {
        primary: '#e74c3c',
        secondary: '#c0392b',
        background: 'rgba(231, 76, 60, 0.1)',
        gradient: ['#e74c3c', '#ec4899']
    },
    hrv: {
        primary: '#f39c12',
        secondary: '#e67e22',
        background: 'rgba(243, 156, 18, 0.1)',
        gradient: ['#f39c12', '#f59e0b']
    },
    goal: '#10b981',
    average: '#6b7280',
    trend: '#8b5cf6'
};

/**
 * Initialize all week view charts
 */
function initializeWeekCharts() {
    console.log('Initializing week view charts...');
    
    // Initialize each chart type
    initializeStepsChart();
    initializeWeightChart();
    initializeHeartRateChart();
    initializeSleepChart();
    initializeHRVChart();
}

/**
 * Initialize steps bar chart (delegates to dedicated steps chart module)
 */
async function initializeStepsChart() {
    if (window.StepsChart) {
        const chart = await window.StepsChart.init('steps-week-chart');
        if (chart) {
            window.WeekCharts.steps = window.StepsChart;
        }
    } else {
        console.warn('StepsChart module not loaded');
    }
}

/**
 * Initialize weight line chart (delegates to dedicated weight chart module)
 */
async function initializeWeightChart() {
    if (window.WeightChart) {
        const chart = await window.WeightChart.init('weight-week-chart');
        if (chart) {
            window.WeekCharts.weight = window.WeightChart;
        }
    } else {
        console.warn('WeightChart module not loaded');
    }
}

/**
 * Initialize heart rate line chart (delegates to dedicated heart rate chart module)
 */
async function initializeHeartRateChart() {
    if (window.HeartRateChart) {
        const chart = await window.HeartRateChart.init('heart-rate-week-chart');
        if (chart) {
            window.WeekCharts.heartRate = window.HeartRateChart;
        }
    } else {
        console.warn('HeartRateChart module not loaded');
    }
}

/**
 * Initialize sleep bar chart
 */
async function initializeSleepChart() {
    const canvas = document.getElementById('sleep-week-chart');
    if (!canvas) {
        console.warn('Sleep chart canvas not found');
        return;
    }

    try {
        const data = await fetchChartData('sleep', 'week');
        const ctx = canvas.getContext('2d');
        
        if (window.WeekCharts.sleep) {
            window.WeekCharts.sleep.destroy();
        }

        window.WeekCharts.sleep = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Sleep Hours',
                        data: data.values.map(v => v / 60), // Convert minutes to hours
                        backgroundColor: createGradient(ctx, ChartColors.sleep.gradient),
                        borderColor: ChartColors.sleep.primary,
                        borderWidth: 2,
                        borderRadius: 4,
                        borderSkipped: false,
                    },
                    {
                        label: 'Goal',
                        data: Array(data.labels.length).fill(8),
                        type: 'line',
                        borderColor: ChartColors.goal,
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                    }
                ]
            },
            options: {
                ...getBaseChartOptions(),
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 12,
                        ticks: {
                            callback: function(value) {
                                return value + 'h';
                            }
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.datasetIndex === 0) {
                                    return `Sleep: ${context.parsed.y.toFixed(1)}h`;
                                } else {
                                    return `Goal: ${context.parsed.y}h`;
                                }
                            }
                        }
                    }
                }
            }
        });

        console.log('Sleep chart initialized successfully');
    } catch (error) {
        console.error('Error initializing sleep chart:', error);
        showChartError(canvas, 'Failed to load sleep data');
    }
}

/**
 * Initialize HRV scatter chart (delegates to dedicated HRV chart module)
 */
async function initializeHRVChart() {
    if (window.HRVChart) {
        const chart = await window.HRVChart.init('hrv-week-chart');
        if (chart) {
            window.WeekCharts.hrv = window.HRVChart;
        }
    } else {
        console.warn('HRVChart module not loaded');
    }
}

/**
 * Fetch chart data from API
 */
async function fetchChartData(metric, period) {
    try {
        const response = await fetch(`/api/charts/${metric}?period=${period}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${metric} chart data:`, error);
        // Return mock data for development
        return generateMockChartData(metric, period);
    }
}

/**
 * Generate mock chart data for development
 */
function generateMockChartData(metric, period) {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const mockData = {
        labels: days,
        values: [],
        trend: 'stable'
    };

    switch (metric) {
        case 'steps':
            mockData.values = [8500, 9200, 7800, 10500, 11200, 6800, 9500];
            mockData.trend = 'up';
            break;
        case 'sleep':
            mockData.values = [420, 450, 480, 390, 510, 540, 420]; // minutes
            mockData.trend = 'stable';
            break;
        case 'weight':
            mockData.values = [75.2, 75.1, 75.3, 75.0, 74.9, 75.1, 75.0];
            mockData.movingAverage = [75.2, 75.15, 75.2, 75.15, 75.1, 75.08, 75.05];
            mockData.trend = 'down';
            break;
        case 'heart_rate':
            mockData.values = [72, 74, 71, 73, 70, 75, 72];
            mockData.trend = 'stable';
            break;
        case 'hrv':
            // Sparse manual data
            mockData.values = [45, null, 42, null, null, 48, null];
            mockData.values = mockData.values.filter(v => v !== null);
            mockData.labels = ['Mon', 'Wed', 'Sat'];
            mockData.trend = 'stable';
            break;
    }

    return mockData;
}

/**
 * Create gradient for chart backgrounds
 */
function createGradient(ctx, colors) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, colors[0]);
    gradient.addColorStop(1, colors[1]);
    return gradient;
}

/**
 * Get base chart options optimized for 7-inch touchscreen
 */
function getBaseChartOptions() {
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
            mode: 'nearest',
            intersect: false
        }
    };
}

/**
 * Update trend summary for charts
 */
function updateTrendSummary(chartType, trend) {
    const summaryElement = document.getElementById(`${chartType}-trend-summary`);
    if (!summaryElement) return;

    const trendConfig = {
        up: { arrow: '↗', text: 'Improving', class: 'trend-up' },
        down: { arrow: '↘', text: 'Declining', class: 'trend-down' },
        stable: { arrow: '→', text: 'Stable', class: 'trend-flat' }
    };

    const config = trendConfig[trend] || trendConfig.stable;
    
    summaryElement.innerHTML = `
        <span class="trend-arrow ${config.class}">${config.arrow}</span>
        <span class="trend-text">${config.text} this week</span>
    `;
}

/**
 * Show error message in chart container
 */
function showChartError(canvas, message) {
    const container = canvas.closest('.chart-body');
    if (container) {
        container.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #64748b;">
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📊</div>
                    <div style="font-size: 0.875rem;">${message}</div>
                </div>
            </div>
        `;
    }
}

/**
 * Destroy all week charts (cleanup function)
 */
function destroyWeekCharts() {
    Object.values(window.WeekCharts).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    window.WeekCharts = {};
}

// Export functions for global access
window.initializeWeekCharts = initializeWeekCharts;
window.destroyWeekCharts = destroyWeekCharts;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure all elements are rendered
    setTimeout(() => {
        if (document.getElementById('steps-week-chart')) {
            initializeWeekCharts();
        }
    }, 100);
});

console.log('Charts.js loaded successfully');