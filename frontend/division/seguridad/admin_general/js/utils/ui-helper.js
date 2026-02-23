/**
 * UIHelper - Centralized UI logic for RID views
 * P1: DRY implementation.
 */
(function () {
    window.RID = window.RID || {};

    // Internal formatter
    const fmt = new Intl.NumberFormat('es-CL');

    const UI = {
        /**
         * Render a KPI value with delta/trend indicator
         * @param {string} valId - Element ID for main value
         * @param {string} deltaId - Element ID for delta/trend
         * @param {number|string} value - Main numeric value
         * @param {number} deltaPct - Percentage delta (-100 to 100)
         * @param {boolean} inverse - If true, negative delta is good (e.g. crimes)
         * @param {string} suffix - Text suffix for delta (e.g. "vs sem. ant.")
         */
        renderKpi(valId, deltaId, value, deltaPct, inverse = true, suffix = "") {
            const valEl = document.getElementById(valId);
            const deltaEl = document.getElementById(deltaId);

            if (valEl) {
                // Handle null/undef gracefully
                const safeVal = (value === null || value === undefined) ? '--' : value;
                valEl.textContent = (typeof safeVal === 'number') ? fmt.format(safeVal) : safeVal;
            }

            if (deltaEl) {
                if (deltaPct === null || deltaPct === undefined || isNaN(deltaPct)) {
                    deltaEl.textContent = '--';
                    deltaEl.className = 'kpi-change kpi-change--neutral';
                    return;
                }

                const arrow = deltaPct >= 0 ? '▲' : '▼';
                const sign = deltaPct >= 0 ? '+' : '';
                const pct = Math.abs(deltaPct).toFixed(1) + '%';

                // Color Logic
                // If inverse=true (crime): + is bad (red/negative), - is good (green/positive)
                // If inverse=false (detection): + is good (green/positive), - is bad (red/negative)
                let className = 'kpi-change';

                /* 
                   kpi-change--negative usually means RED (bad)
                   kpi-change--positive usually means GREEN (good)
                */
                if (deltaPct > 0) className += inverse ? ' kpi-change--negative' : ' kpi-change--positive';
                else if (deltaPct < 0) className += inverse ? ' kpi-change--positive' : ' kpi-change--negative';
                else className += ' kpi-change--neutral'; // 0%

                deltaEl.innerHTML = `${arrow} ${pct} <span style="font-size:0.8em; opacity:0.8">${suffix}</span>`;
                deltaEl.className = className;
            }
        },

        /**
         * Render generic text content safely
         */
        setText(id, text) {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        },

        setHtml(id, html) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = html;
        },

        renderColoredPercent(id, pct, inverse = true) {
            const el = document.getElementById(id);
            if (!el || pct === null || isNaN(pct)) return;

            const val = parseFloat(pct);
            const sign = val > 0 ? '+' : '';
            el.textContent = `${sign}${val.toFixed(1)}%`;

            // Color logic: if inverse=true (crime), growth (>0) is bad (danger)
            const isBad = inverse ? (val > 0) : (val < 0);
            el.style.color = isBad ? '#ef4444' : '#10b981'; // Tailwind colors used in styles
        },

        fillHeaders(comuna, semana) {
            document.querySelectorAll('.comuna-fill').forEach(el => el.textContent = comuna || 'Cargando...');

            // Standardize week format to "Semana XX/YYYY"
            let formattedSemana = semana || '--';
            if (formattedSemana && formattedSemana.includes(' del ')) {
                formattedSemana = formattedSemana.replace(/ del /i, '/').replace(/Semana /i, 'Semana ');
            }

            document.querySelectorAll('.semana-fill').forEach(el => el.textContent = formattedSemana);
        },

        formatNumber(n) { return (n !== null && n !== undefined) ? fmt.format(n) : '--'; }
    };

    window.RID.UI = UI;
    // Alias for partial migration ease
    window.UIHelper = UI;
})();
