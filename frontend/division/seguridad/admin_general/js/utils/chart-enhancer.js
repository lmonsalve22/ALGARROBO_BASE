/**
 * Chart Migration Script
 * Aplica automáticamente las mejoras visuales a todos los gráficos de la aplicación
 * 
 * Mejoras aplicadas:
 * #1 - Gradientes en barras
 * #2 - Sombras en gráficos  
 * #3 - Paleta coordinada
 * #5 - Bordes redondeados (8px)
 * #6 - Tipografía Outfit
 * #10 - Footer de fuente
 * #11 - Paleta semántica delitos
 * #13 - Colores de variación
 * #14 - Trendline
 * #15 - Énfasis en máximos
 * #16 - Línea de promedio
 * #21 - Formato chileno
 * #31/#32 - Data labels con %
 */

const ChartEnhancer = {
    /**
     * Auto-enhance all charts after they are created
     */
    enhanceAllCharts() {
        if (typeof Chart === 'undefined') return;

        // Store original Chart constructor
        const OriginalChart = Chart;

        // Apply global defaults
        this.applyGlobalDefaults();

        console.log('✅ ChartEnhancer: Global Chart.js defaults applied');
    },

    /**
     * Apply global Chart.js defaults for all charts
     */
    applyGlobalDefaults() {
        // #6 - Outfit font globally
        Chart.defaults.font.family = 'Outfit, sans-serif';
        Chart.defaults.font.weight = '500';
        Chart.defaults.color = '#64748b';

        // #5 - Border radius for bars
        Chart.defaults.elements.bar.borderRadius = 8;
        Chart.defaults.elements.bar.borderSkipped = false;

        // Line chart defaults
        Chart.defaults.elements.line.tension = 0.4;
        Chart.defaults.elements.line.borderWidth = 2.5;

        // Point defaults
        Chart.defaults.elements.point.radius = 4;
        Chart.defaults.elements.point.hoverRadius = 6;
        Chart.defaults.elements.point.borderWidth = 2;
        Chart.defaults.elements.point.backgroundColor = '#fff';

        // Arc defaults (doughnut/pie)
        Chart.defaults.elements.arc.borderWidth = 2;
        Chart.defaults.elements.arc.borderColor = '#fff';

        // Legend defaults
        Chart.defaults.plugins.legend.labels.font = {
            family: 'Outfit, sans-serif',
            size: 11,
            weight: '500'
        };
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 15;

        // Tooltip defaults
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
        Chart.defaults.plugins.tooltip.titleFont = {
            family: 'Outfit, sans-serif',
            size: 13,
            weight: '600'
        };
        Chart.defaults.plugins.tooltip.bodyFont = {
            family: 'Outfit, sans-serif',
            size: 12
        };
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.displayColors = true;
        Chart.defaults.plugins.tooltip.boxPadding = 6;

        // Scale defaults
        Chart.defaults.scales.linear.grid = {
            color: 'rgba(226, 232, 240, 0.8)',
            drawBorder: false
        };
        Chart.defaults.scales.category.grid = {
            display: false
        };
    },

    /**
     * Enhance a specific chart instance with premium features
     * @param {Chart} chart - Chart.js instance
     * @param {Object} options - Enhancement options
     */
    enhanceChart(chart, options = {}) {
        const ctx = chart.ctx;
        const type = chart.config.type;

        // Apply shadow to canvas container
        if (options.shadow !== false) {
            ChartHelper.applyShadow(chart.canvas);
        }

        // Add gradient backgrounds for bar charts
        if (type === 'bar' && options.gradients !== false) {
            chart.data.datasets.forEach((dataset, idx) => {
                if (!dataset._hasGradient) {
                    const colorConfig = ChartHelper.colors.bars[idx % ChartHelper.colors.bars.length];
                    const gradient = ctx.createLinearGradient(0, 0, 0, chart.chartArea?.height || 400);
                    gradient.addColorStop(0, colorConfig.gradient[0]);
                    gradient.addColorStop(1, colorConfig.gradient[1]);
                    dataset.backgroundColor = gradient;
                    dataset._hasGradient = true;
                }
            });
            chart.update('none');
        }

        // Add area fill for line charts
        if (type === 'line' && options.areaFill !== false) {
            chart.data.datasets.forEach((dataset, idx) => {
                if (dataset.fill && !dataset._hasGradient) {
                    const gradient = ctx.createLinearGradient(0, 0, 0, chart.chartArea?.height || 300);
                    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
                    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.02)');
                    dataset.backgroundColor = gradient;
                    dataset._hasGradient = true;
                }
            });
            chart.update('none');
        }
    },

    /**
     * Format all numbers in the view using Chilean format
     */
    formatViewNumbers() {
        // Find elements with data-format attribute
        document.querySelectorAll('[data-format="number"]').forEach(el => {
            const value = parseFloat(el.textContent.replace(/[^\d.-]/g, ''));
            if (!isNaN(value)) {
                el.textContent = ChartHelper.formatNumber(value);
            }
        });

        document.querySelectorAll('[data-format="percent"]').forEach(el => {
            const value = parseFloat(el.textContent.replace(/[^\d.-]/g, ''));
            if (!isNaN(value)) {
                el.textContent = ChartHelper.formatPercent(value);
            }
        });
    },

    /**
     * Add source footer to all chart containers
     * @param {string} source - Source type: 'STOP', 'CEAD', 'MIXED', 'INE'
     */
    addSourceFooters(source = 'STOP') {
        document.querySelectorAll('.chart-card, .chart-card-premium').forEach(container => {
            // Check if footer already exists
            if (!container.querySelector('.chart-source-footer')) {
                const footer = document.createElement('div');
                footer.className = 'chart-source-footer';
                footer.innerHTML = ChartHelper.getSourceFooterHtml(source).replace('<div class="chart-source-footer">', '').replace('</div>', '');
                container.appendChild(footer);
            }
        });
    },

    /**
     * Apply striped styling to all tables
     */
    applyTableStyling() {
        document.querySelectorAll('table.table, table.data-table').forEach(table => {
            if (!table.classList.contains('table-striped')) {
                table.classList.add('table-striped');
            }
            if (!table.classList.contains('data-table-bordered')) {
                table.classList.add('data-table-bordered');
            }
        });
    },

    /**
     * Apply variation colors to elements with delta values
     */
    applyVariationColors() {
        document.querySelectorAll('[data-delta]').forEach(el => {
            const delta = parseFloat(el.dataset.delta);
            el.classList.remove('var-increase', 'var-decrease', 'var-neutral');
            el.classList.add(ChartHelper.getVariationClass(delta));
        });
    },

    /**
     * Get appropriate source type based on current view
     */
    getSourceForView(viewId) {
        const viewNum = parseInt(viewId.replace('vista', ''));
        const ceadViews = [4, 7, 10, 11, 12, 15, 16, 19, 20, 21, 25];
        const ineViews = [1, 9, 10, 12, 13, 17];
        const hybridViews = [41, 42, 43, 44, 45];

        if (hybridViews.includes(viewNum)) return 'MIXED';
        if (ceadViews.includes(viewNum)) {
            return ineViews.includes(viewNum) ? 'MIXED' : 'CEAD';
        }
        if (ineViews.includes(viewNum)) return 'MIXED';

        return 'STOP';
    }
};

// Initialize enhancer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for Chart.js
    const waitForChart = setInterval(() => {
        if (typeof Chart !== 'undefined') {
            clearInterval(waitForChart);
            ChartEnhancer.enhanceAllCharts();
        }
    }, 100);
});

// Expose globally
window.ChartEnhancer = ChartEnhancer;
