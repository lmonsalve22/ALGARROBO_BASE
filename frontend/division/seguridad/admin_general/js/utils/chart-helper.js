/**
 * Chart Initialization Helper - Premium Configuration
 * Mejoras aplicadas:
 * #1 - Gradientes en barras
 * #2 - Sombras en gráficos
 * #3 - Paleta coordinada con variables CSS
 * #5 - Bordes redondeados uniformes (8px)
 * #6 - Tipografía Outfit en Chart.js
 * #11 - Doughnut con indicador central
 * #14 - Líneas de tendencia
 * #21 - Formato numérico chileno
 */

const ChartHelper = {
    /**
     * Initialize charts with retry logic
     */
    init(initFunction, maxRetries = 50) {
        let attempts = 0;

        const tryInit = () => {
            if (typeof Chart !== 'undefined') {
                try {
                    initFunction();
                } catch (error) {
                    console.error('Error initializing charts:', error);
                }
            } else if (attempts < maxRetries) {
                attempts++;
                setTimeout(tryInit, 100);
            } else {
                console.error('Chart.js not available after max retries');
            }
        };

        tryInit();
    },

    /**
     * Destroy all Chart.js instances to prevent memory leaks when changing views.
     */
    destroyAllCharts: function () {
        if (typeof Chart !== 'undefined') {
            const charts = Object.values(Chart.instances || {});
            charts.forEach(chart => {
                try {
                    chart.destroy();
                } catch (e) {
                    console.warn('Error destroying chart:', e);
                }
            });
            console.log("🧹 Charts cleaned up");
        }
    },

    /**
     * #21 - Formato numérico chileno (1.234,56)
     */
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return new Intl.NumberFormat('es-CL', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(value);
    },

    /**
     * Format percentage Chilean style
     */
    formatPercent(value, decimals = 1) {
        if (value === null || value === undefined || isNaN(value)) return '--';
        const sign = value >= 0 ? '+' : '';
        return `${sign}${this.formatNumber(value, decimals)}%`;
    },

    /**
     * #1 - Create gradient for bars
     */
    createGradient(ctx, colorStart, colorEnd, vertical = true) {
        const gradient = vertical
            ? ctx.createLinearGradient(0, 0, 0, 400)
            : ctx.createLinearGradient(0, 0, 400, 0);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    },

    /**
     * #1 - Predefined gradient pairs
     */
    gradients: {
        blue: ['#3b82f6', '#1d4ed8'],
        red: ['#ef4444', '#b91c1c'],
        green: ['#10b981', '#047857'],
        orange: ['#f59e0b', '#d97706'],
        purple: ['#8b5cf6', '#6d28d9'],
        gray: ['#64748b', '#475569'],
        pink: ['#ec4899', '#be185d']
    },

    /**
     * Get gradient background for dataset
     */
    getGradientBackground(ctx, colorName) {
        const colors = this.gradients[colorName] || this.gradients.blue;
        return this.createGradient(ctx, colors[0], colors[1]);
    },

    /**
     * #3 - Paleta de colores coordinada (CSS variables compatible)
     */
    colors: {
        // Primary palette
        primary: '#3b82f6',
        primaryLight: '#60a5fa',
        primaryDark: '#1d4ed8',

        // Semantic colors
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#06b6d4',

        // Neutral
        gray: '#64748b',
        grayLight: '#94a3b8',
        grayDark: '#475569',

        // Categorical (for multiple series)
        categorical: ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'],

        // Sequential (for intensity)
        sequential: ['#dbeafe', '#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'],

        // For bar charts with gradient support
        bars: [
            { solid: '#3b82f6', gradient: ['#60a5fa', '#2563eb'] },
            { solid: '#ef4444', gradient: ['#f87171', '#dc2626'] },
            { solid: '#f59e0b', gradient: ['#fbbf24', '#d97706'] },
            { solid: '#10b981', gradient: ['#34d399', '#059669'] },
            { solid: '#8b5cf6', gradient: ['#a78bfa', '#7c3aed'] },
            { solid: '#64748b', gradient: ['#94a3b8', '#475569'] }
        ],

        // #11 - Paleta semántica de delitos
        delitos: {
            'ROBO CON VIOLENCIA': '#ef4444',
            'ROBO CON INTIMIDACION': '#ef4444',
            'ROBO EN LUGAR HABITADO': '#f59e0b',
            'ROBO EN LUGAR NO HABITADO': '#f59e0b',
            'ROBO DE VEHICULO': '#dc2626',
            'HURTO': '#3b82f6',
            'HURTO SIMPLE': '#3b82f6',
            'LESIONES': '#8b5cf6',
            'LESIONES GRAVES': '#7c3aed',
            'HOMICIDIO': '#991b1b',
            'DROGAS': '#10b981',
            'OTROS': '#64748b',
            'default': '#94a3b8'
        },

        // #13 - Colores para variaciones
        variation: {
            increase: '#ef4444',   // Rojo = aumento = malo
            decrease: '#10b981',   // Verde = disminución = bueno
            neutral: '#64748b'
        }
    },

    /**
     * #11 - Get color for delito type
     */
    getDelitoColor(delitoName) {
        if (!delitoName) return this.colors.delitos.default;
        const normalizedName = delitoName.toUpperCase().trim();

        // Find matching color
        for (const [key, color] of Object.entries(this.colors.delitos)) {
            if (normalizedName.includes(key) || key.includes(normalizedName)) {
                return color;
            }
        }
        return this.colors.delitos.default;
    },

    /**
     * #11 - Get array of delito colors for datasets
     */
    getDelitoColors(delitoNames) {
        return delitoNames.map(name => this.getDelitoColor(name));
    },

    /**
     * #13 - Get variation color
     */
    getVariationColor(value) {
        if (value > 0) return this.colors.variation.increase;
        if (value < 0) return this.colors.variation.decrease;
        return this.colors.variation.neutral;
    },

    /**
     * #13 - Get variation class
     */
    getVariationClass(value) {
        if (value > 0) return 'var-increase';
        if (value < 0) return 'var-decrease';
        return 'var-neutral';
    },

    /**
     * #15 - Find max index in data array
     */
    findMaxIndex(data) {
        if (!data || data.length === 0) return -1;
        let maxIdx = 0;
        let maxVal = data[0];
        data.forEach((val, idx) => {
            if (val > maxVal) {
                maxVal = val;
                maxIdx = idx;
            }
        });
        return maxIdx;
    },

    /**
     * #15 - Highlight max value in bar chart
     */
    getBarColorsWithMaxHighlight(data, baseColor = '#3b82f6', maxColor = '#f59e0b') {
        const maxIdx = this.findMaxIndex(data);
        return data.map((_, idx) => idx === maxIdx ? maxColor : baseColor);
    },

    /**
     * #16 - Create average line annotation
     */
    getAverageLineAnnotation(data, label = 'Promedio', color = '#64748b') {
        const avg = data.reduce((a, b) => a + b, 0) / data.length;
        return {
            type: 'line',
            borderColor: color,
            borderWidth: 2,
            borderDash: [6, 4],
            label: {
                display: true,
                content: `${label}: ${this.formatNumber(avg, 1)}`,
                position: 'end',
                backgroundColor: color,
                font: { family: 'Outfit, sans-serif', size: 10, weight: '600' },
                padding: 4
            },
            scaleID: 'y',
            value: avg
        };
    },

    /**
     * #31, #32 - Data labels configuration for bars
     */
    getBarDataLabelsConfig(data, total = null, showPercent = true) {
        const dataTotal = total || data.reduce((a, b) => a + b, 0);
        return {
            display: true,
            anchor: 'end',
            align: 'top',
            offset: 4,
            color: '#1e293b',
            font: {
                family: 'Outfit, sans-serif',
                size: 11,
                weight: '700'
            },
            formatter: (value) => {
                if (showPercent && dataTotal > 0) {
                    const pct = ((value / dataTotal) * 100).toFixed(1);
                    return `${this.formatNumber(value)} (${pct}%)`;
                }
                return this.formatNumber(value);
            }
        };
    },

    /**
     * #10 - Generate source footer HTML
     */
    getSourceFooterHtml(source = 'STOP') {
        const sourceMap = {
            'STOP': 'Fuente: Sistema Táctico de Operación Policial (STOP)',
            'CEAD': 'Fuente: Centro de Análisis del Delito (CEAD)',
            'INE': 'Fuente: Instituto Nacional de Estadísticas (INE)',
            'MIXED': 'Fuente: STOP + CEAD'
        };
        return `<div class="chart-source-footer">${sourceMap[source] || source}</div>`;
    },

    /**
     * #5 & #6 - Default chart options with rounded corners and Outfit font
     */
    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    font: { family: 'Outfit, sans-serif', size: 11, weight: '500' },
                    padding: 15,
                    usePointStyle: true,
                    pointStyle: 'rectRounded'
                }
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                titleFont: { family: 'Outfit, sans-serif', size: 13, weight: '600' },
                bodyFont: { family: 'Outfit, sans-serif', size: 12 },
                padding: 12,
                cornerRadius: 8,
                displayColors: true,
                boxPadding: 6
            }
        },
        elements: {
            bar: {
                borderRadius: 8,        // #5 - Bordes redondeados
                borderSkipped: false
            },
            line: {
                tension: 0.4,
                borderWidth: 2.5
            },
            point: {
                radius: 4,
                hoverRadius: 6,
                borderWidth: 2,
                backgroundColor: '#fff'
            },
            arc: {
                borderWidth: 2,
                borderColor: '#fff'
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    font: { family: 'Outfit, sans-serif', size: 10, weight: '500' },
                    color: '#64748b'
                }
            },
            y: {
                grid: {
                    color: 'rgba(226, 232, 240, 0.8)',
                    drawBorder: false
                },
                ticks: {
                    font: { family: 'Outfit, sans-serif', size: 10, weight: '500' },
                    color: '#64748b',
                    callback: function (value) {
                        return ChartHelper.formatNumber(value);
                    }
                }
            }
        }
    },

    /**
     * #11 - Doughnut center text plugin
     */
    doughnutCenterPlugin: {
        id: 'doughnutCenterText',
        beforeDraw: function (chart) {
            if (chart.config.type !== 'doughnut') return;
            if (!chart.config.options.plugins.centerText) return;

            const { ctx, chartArea: { top, bottom, left, right } } = chart;
            const centerConfig = chart.config.options.plugins.centerText;

            const centerX = (left + right) / 2;
            const centerY = (top + bottom) / 2;

            ctx.save();

            // Main value
            ctx.font = `bold ${centerConfig.fontSize || 28}px Outfit, sans-serif`;
            ctx.fillStyle = centerConfig.color || '#1e293b';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(centerConfig.value || '', centerX, centerY - 8);

            // Label
            if (centerConfig.label) {
                ctx.font = '500 12px Outfit, sans-serif';
                ctx.fillStyle = '#64748b';
                ctx.fillText(centerConfig.label, centerX, centerY + 14);
            }

            ctx.restore();
        }
    },

    /**
     * #14 - Calculate linear trendline
     */
    calculateTrendline(data) {
        const n = data.length;
        if (n < 2) return data;

        let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        data.forEach((y, x) => {
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        });

        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const intercept = (sumY - slope * sumX) / n;

        return data.map((_, x) => slope * x + intercept);
    },

    /**
     * #14 - Create trendline dataset
     */
    createTrendlineDataset(data, label = 'Tendencia', color = '#ef4444') {
        const trendData = this.calculateTrendline(data);
        return {
            label: label,
            data: trendData,
            borderColor: color,
            borderWidth: 2,
            borderDash: [8, 4],
            pointRadius: 0,
            fill: false,
            tension: 0
        };
    },

    /**
     * #14 - Add trendline annotation
     */
    getTrendlineAnnotation(data, color = '#ef4444') {
        const n = data.length;
        if (n < 2) return null;

        const trendData = this.calculateTrendline(data);
        const startY = trendData[0];
        const endY = trendData[n - 1];

        return {
            type: 'line',
            borderColor: color,
            borderWidth: 2,
            borderDash: [6, 4],
            label: {
                display: true,
                content: 'Tendencia',
                position: 'end',
                backgroundColor: color,
                font: { family: 'Outfit, sans-serif', size: 10, weight: '600' },
                padding: 4
            },
            xMin: 0,
            xMax: n - 1,
            yMin: startY,
            yMax: endY
        };
    },

    /**
     * #2 - Apply shadow to chart canvas
     */
    applyShadow(chartElement) {
        if (chartElement && chartElement.parentElement) {
            chartElement.parentElement.style.cssText += `
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
                border-radius: 12px;
                background: white;
                padding: 1rem;
            `;
        }
    },

    /**
     * Merge options with defaults
     */
    mergeOptions(customOptions = {}) {
        return this.deepMerge(this.defaultOptions, customOptions);
    },

    /**
     * Deep merge utility
     */
    deepMerge(target, source) {
        const output = { ...target };
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                output[key] = this.deepMerge(output[key] || {}, source[key]);
            } else {
                output[key] = source[key];
            }
        }
        return output;
    },

    /**
     * Get bar datasets with gradients
     */
    getBarDatasets(ctx, datasets) {
        return datasets.map((ds, i) => {
            const colorConfig = this.colors.bars[i % this.colors.bars.length];
            const gradient = this.createGradient(ctx, colorConfig.gradient[0], colorConfig.gradient[1]);

            return {
                ...ds,
                backgroundColor: gradient,
                borderRadius: 8,
                borderSkipped: false
            };
        });
    },

    /**
     * Create a fully configured bar chart
     */
    createBarChart(canvasId, labels, datasets, customOptions = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');

        // Apply gradients to datasets
        const styledDatasets = this.getBarDatasets(ctx, datasets);

        // Apply shadow to container
        this.applyShadow(canvas);

        const options = this.mergeOptions(customOptions);

        return new Chart(ctx, {
            type: 'bar',
            data: { labels, datasets: styledDatasets },
            options
        });
    },

    /**
     * Create a fully configured line chart with optional trendline
     */
    createLineChart(canvasId, labels, datasets, customOptions = {}, includeTrendline = false) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');

        // Apply shadow
        this.applyShadow(canvas);

        // Add trendline if requested
        let finalDatasets = [...datasets];
        if (includeTrendline && datasets.length > 0) {
            const mainData = datasets[0].data;
            const trendlineDs = this.createTrendlineDataset(mainData);
            finalDatasets.push(trendlineDs);
        }

        const options = this.mergeOptions(customOptions);

        return new Chart(ctx, {
            type: 'line',
            data: { labels, datasets: finalDatasets },
            options
        });
    },

    /**
     * #11 - Create doughnut with center text
     */
    createDoughnutChart(canvasId, labels, data, centerText = null, customOptions = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');

        // Apply shadow
        this.applyShadow(canvas);

        // Register center plugin
        if (!Chart.registry.plugins.get('doughnutCenterText')) {
            Chart.register(this.doughnutCenterPlugin);
        }

        const total = data.reduce((a, b) => a + b, 0);

        const options = this.mergeOptions({
            cutout: '55%',
            plugins: {
                centerText: centerText || {
                    value: this.formatNumber(total),
                    label: 'Total Casos',
                    fontSize: 28,
                    color: '#1e293b'
                },
                legend: {
                    position: 'right',
                    labels: {
                        font: { family: 'Outfit, sans-serif', size: 10 },
                        boxWidth: 12,
                        generateLabels: function (chart) {
                            const data = chart.data;
                            const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                            return data.labels.map((label, i) => {
                                const value = data.datasets[0].data[i];
                                const pct = ((value / total) * 100).toFixed(1);
                                return {
                                    text: `${label}: ${ChartHelper.formatNumber(value)} (${pct}%)`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    hidden: false,
                                    index: i
                                };
                            });
                        }
                    }
                },
                datalabels: {
                    color: '#fff',
                    font: { weight: 'bold', size: 11, family: 'Outfit, sans-serif' },
                    formatter: function (value) {
                        const pct = ((value / total) * 100).toFixed(0);
                        return pct > 5 ? `${ChartHelper.formatNumber(value)}\n(${pct}%)` : '';
                    },
                    textAlign: 'center'
                }
            },
            ...customOptions
        });

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: this.colors.categorical.slice(0, data.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options,
            plugins: [ChartDataLabels]
        });
    }
};

// Register global Chart.js defaults (#6 - Outfit font)
if (typeof Chart !== 'undefined') {
    Chart.defaults.font.family = 'Outfit, sans-serif';
    Chart.defaults.font.weight = '500';
    Chart.defaults.color = '#64748b';

    // Register center text plugin
    Chart.register(ChartHelper.doughnutCenterPlugin);

    // #31 - Global Registration for DataLabels (for PDF/Static focus)
    if (typeof ChartDataLabels !== 'undefined') {
        Chart.register(ChartDataLabels);

        // Define standard global defaults for DataLabels to ensure clean look
        // Explicitly enabling them by default as per user "Zero-Interactivity" request
        Chart.defaults.plugins.datalabels = {
            display: true,
            color: '#1e293b',
            font: {
                family: 'Outfit, sans-serif',
                size: 10,
                weight: '700'
            },
            padding: 4,
            anchor: 'end',
            align: 'top',
            offset: 4,
            formatter: (value) => {
                // Handle both simple numbers and decimal values
                if (typeof value === 'number') {
                    return ChartHelper.formatNumber(value, value % 1 === 0 ? 0 : 1);
                }
                return value;
            }
        };
    }
}

// Expose globally
window.ChartHelper = ChartHelper;
