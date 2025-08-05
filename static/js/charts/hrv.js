/**
 * HRV Scatter Chart - Health Tracker
 * Manual entry visualization for Heart Rate Variability data, optimized for 7-inch touchscreen
 */

// HRV chart configuration and utilities
window.HRVChart = {
    chart: null,
    healthyHRVRange: { min: 20, max: 60 }, // Typical healthy resting HRV range (ms)
    
    /**
     * Initialize HRV scatter chart
     */
    async init(canvasId = 'hrv-week-chart') {
        const canvas = document.getElementById(canvasId);
        const container = document.getElementById('hrv-chart-container');
        
        if (!canvas || !container) {
            console.warn(`HRV chart elements not found: canvas=${!!canvas}, container=${!!container}`);
            return null;
        }

        try {
            // Fetch HRV data from API
            const data = await this.fetchHRVData();
            
            // Handle empty data case
            if (!data.values || data.values.length === 0) {
                this.showEmptyState(container);
                return null;
            }
            
            // Show container and initialize the chart
            container.style.display = 'block';
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
            this.updateHRVTrendSummary(data);
            
            console.log('HRV chart initialized successfully');
            return this.chart;
            
        } catch (error) {
            console.error('Error initializing HRV chart:', error);
            this.showError(canvas, 'Failed to load HRV data');
            return null;
        }
    },

    /**
     * Fetch HRV data from API
     */
    async fetchHRVData() {
        const response = await fetch('/api/charts/hrv?period=week');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate data structure
        if (!data.labels) {
            throw new Error('Invalid HRV chart data structure');
        }
        
        return data;
    },

    /**
     * Create Chart.js configuration for HRV scatter chart
     */
    createChartConfig(data) {
        // Convert to scatter plot data format, filtering out zero/null values
        const scatterData = [];
        const validLabels = [];
        
        data.values.forEach((value, index) => {
            if (value && value > 0) {
                scatterData.push({
                    x: validLabels.length,
                    y: value,
                    label: data.labels[index]
                });
                validLabels.push(data.labels[index]);
            }
        });

        return {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'HRV Measurements',
                        data: scatterData,
                        backgroundColor: scatterData.map(point => 
                            this.getHRVStatusColor(point.y).background
                        ),
                        borderColor: scatterData.map(point => 
                            this.getHRVStatusColor(point.y).border
                        ),
                        borderWidth: 2,
                        pointRadius: 8,
                        pointHoverRadius: 10,
                        pointHoverBorderWidth: 3,
                    },
                    // Healthy range reference area
                    {
                        label: 'Healthy Range (Upper)',
                        data: validLabels.map((_, index) => ({
                            x: index,
                            y: this.healthyHRVRange.max
                        })),
                        borderColor: 'rgba(34, 197, 94, 0.3)',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        showLine: true,
                        tension: 0
                    },
                    {
                        label: 'Healthy Range (Lower)', 
                        data: validLabels.map((_, index) => ({
                            x: index,
                            y: this.healthyHRVRange.min
                        })),
                        borderColor: 'rgba(34, 197, 94, 0.3)',
                        backgroundColor: 'rgba(34, 197, 94, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        fill: '-1', // Fill between this and previous dataset
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        showLine: true,
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
                                const dataPoint = context[0].raw;
                                return dataPoint.label || `Entry ${context[0].dataIndex + 1}`;
                            },
                            label: (context) => {
                                if (context.datasetIndex === 0) {
                                    const hrv = context.parsed.y;
                                    const status = this.getHRVStatus(hrv);
                                    const trend = this.calculateHRVTrend(scatterData, context.dataIndex);
                                    
                                    return [
                                        `HRV: ${hrv} ms`,
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
                        type: 'linear',
                        position: 'bottom',
                        min: -0.5,
                        max: Math.max(0, validLabels.length - 0.5),
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                const index = Math.round(value);
                                return validLabels[index] || '';
                            },
                            font: {
                                size: 11,
                                weight: '500'
                            },
                            color: '#64748b'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: false,
                        min: Math.max(0, Math.min(...scatterData.map(d => d.y)) - 5),
                        max: Math.max(...scatterData.map(d => d.y)) + 5,
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
                                return value + ' ms';
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
                    mode: 'point',
                    intersect: true
                },
                animation: {
                    duration: 600,
                    easing: 'easeOutCubic'
                },
                // Touch-friendly options
                onHover: (event, elements, chart) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements, chart) => {
                    if (elements.length > 0) {
                        const element = elements[0];
                        const dataPoint = scatterData[element.index];
                        
                        // Provide haptic feedback
                        if (window.HealthTrackerUtils && window.HealthTrackerUtils.hapticFeedback) {
                            window.HealthTrackerUtils.hapticFeedback('light');
                        }
                        
                        console.log(`Clicked on ${dataPoint.label}: ${dataPoint.y} ms HRV`);
                        
                        // Could trigger edit/delete actions for manual entries
                        if (window.showManualEntryEdit) {
                            window.showManualEntryEdit('hrv', dataPoint);
                        }
                    }
                }
            }
        };
    },

    /**
     * Get HRV status classification
     */
    getHRVStatus(hrv) {
        if (hrv < 15) return { emoji: '🔴', text: 'Very Low (Recovery needed)' };
        if (hrv < 20) return { emoji: '🟡', text: 'Low (Monitor stress)' };
        if (hrv <= 60) return { emoji: '🟢', text: 'Healthy Range' };
        if (hrv <= 80) return { emoji: '💪', text: 'Excellent (Athletic)' };
        return { emoji: '⭐', text: 'Outstanding' };
    },

    /**
     * Get color scheme based on HRV value
     */
    getHRVStatusColor(hrv) {
        if (hrv < 20) {
            return { background: '#fecaca', border: '#dc2626' }; // Red for low
        } else if (hrv <= 60) {
            return { background: '#bbf7d0', border: '#16a34a' }; // Green for healthy
        } else {
            return { background: '#ddd6fe', border: '#7c3aed' }; // Purple for excellent
        }
    },

    /**
     * Calculate HRV trend between measurements
     */
    calculateHRVTrend(scatterData, index) {
        if (index === 0 || scatterData.length < 2) return null;
        
        const current = scatterData[index].y;
        const previous = scatterData[index - 1].y;
        const diff = current - previous;
        
        if (Math.abs(diff) <= 2) return '→ Stable';
        return diff > 0 ? `↗ +${diff.toFixed(1)} ms` : `↘ ${diff.toFixed(1)} ms`;
    },

    /**
     * Update HRV trend summary
     */
    updateHRVTrendSummary(data) {
        const summaryElement = document.getElementById('hrv-trend-summary');
        const promptElement = document.getElementById('hrv-entry-prompt');
        
        if (!summaryElement) return;

        try {
            const validValues = data.values.filter(v => v && v > 0);
            const entryCount = validValues.length;
            
            if (entryCount === 0) {
                // Hide trend summary, show entry prompt
                summaryElement.style.display = 'none';
                if (promptElement) {
                    promptElement.style.display = 'flex';
                }
                return;
            }

            // Show trend summary, hide entry prompt
            summaryElement.style.display = 'flex';
            summaryElement.classList.add('visible');
            if (promptElement) {
                promptElement.style.display = 'none';
                promptElement.classList.add('hidden');
            }

            const avgHRV = Math.round(validValues.reduce((sum, v) => sum + v, 0) / validValues.length);
            const trend = data.trend || 'stable';
            
            // Get trend configuration
            const trendConfig = {
                stable: { arrow: '→', text: 'Stable patterns', class: 'trend-flat' },
                up: { arrow: '↗', text: 'Improving', class: 'trend-up' },
                down: { arrow: '↘', text: 'Declining', class: 'trend-down' }
            };
            
            const config = trendConfig[trend] || trendConfig.stable;
            const status = this.getHRVStatus(avgHRV);
            
            summaryElement.innerHTML = `
                <span class="trend-arrow ${config.class}">${config.arrow}</span>
                <span class="trend-text">${config.text}</span>
                <span class="hrv-status">(${entryCount} entries, avg: ${avgHRV}ms ${status.emoji})</span>
            `;
            
        } catch (error) {
            console.error('Error updating HRV trend summary:', error);
        }
    },

    /**
     * Show empty state when no HRV data
     */
    showEmptyState(container) {
        container.style.display = 'block';
        const chartBody = container.querySelector('.chart-body');
        
        if (chartBody) {
            chartBody.innerHTML = `
                <div class="hrv-empty-state">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">💓</div>
                    <div style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">
                        Start tracking your HRV
                    </div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1.5rem; text-align: center; line-height: 1.4;">
                        Heart Rate Variability helps monitor recovery and stress levels.<br>
                        Log your morning HRV to see trends over time.
                    </div>
                    <button onclick="showManualEntry('hrv')" 
                            style="padding: 0.75rem 1.5rem; background: var(--accent-color); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                        Add First Entry
                    </button>
                </div>
            `;
        }
        
        console.log('HRV chart showing empty state');
    },

    /**
     * Update chart with new data
     */
    async refresh() {
        if (!this.chart) {
            // Try to re-initialize if chart doesn't exist
            return await this.init();
        }
        
        try {
            const data = await this.fetchHRVData();
            
            // Handle empty data case
            if (!data.values || data.values.length === 0) {
                this.destroy();
                const container = document.getElementById('hrv-chart-container');
                if (container) {
                    this.showEmptyState(container);
                }
                return;
            }
            
            // Recreate the chart with new data
            const canvas = document.getElementById('hrv-week-chart');
            if (canvas) {
                this.destroy();
                await this.init();
            }
            
            console.log('HRV chart refreshed');
            
        } catch (error) {
            console.error('Error refreshing HRV chart:', error);
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
                    <div style="font-size: 2rem; margin-bottom: 1rem;">💓</div>
                    <div style="font-size: 0.875rem; color: #ef4444;">${message}</div>
                    <button onclick="window.HRVChart.init()" 
                            style="margin-top: 1rem; padding: 0.5rem 1rem; background: #f39c12; color: white; border: none; border-radius: 0.375rem; cursor: pointer;">
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
        if (document.getElementById('hrv-week-chart')) {
            window.HRVChart.init();
        }
    }, 500); // Slight delay to ensure other charts load first
});

// Export for global access
window.HRVChart = window.HRVChart;

// Integration with main charts system
if (window.WeekCharts) {
    window.WeekCharts.hrv = window.HRVChart;
}

console.log('HRV chart module loaded');