/**
 * Centralized Data Waiter Utility (ERR-002 / CQ-001 Fix)
 * Replaces ~27 inline waitForData implementations across vistas.
 *
 * Usage in vistas:
 *   await waitForData();                  // Waits for STATE_DATA (default)
 *   await waitForData('STATE_DATA_CEAD'); // Waits for CEAD data
 *   await waitForData('COMUNAS_DATA', 10000, d => d && d.length > 0); // Custom condition
 */

/**
 * Wait for a global data object to be ready.
 * @param {string}   dataKey    - Key on `window` to poll (default: 'STATE_DATA')
 * @param {number}   timeoutMs  - Max wait in ms (default: 15000)
 * @param {Function} [condition] - Custom readiness predicate. Receives window[dataKey].
 *                                 Default: checks `obj.isLoaded === true`
 * @returns {Promise<any>} Resolves with the data object, rejects on timeout.
 */
window.waitForData = function (dataKey = 'STATE_DATA', timeoutMs = 15000, condition) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();

        // Default condition: object exists and has isLoaded flag
        const isReady = condition || ((obj) => obj && obj.isLoaded);

        const check = () => {
            const data = window[dataKey];
            if (isReady(data)) {
                resolve(data);
                return;
            }

            if (Date.now() - startTime > timeoutMs) {
                LOG.error(`❌ waitForData timeout: ${dataKey} no cargó en ${timeoutMs}ms.`);
                reject(new Error(`Timeout waiting for ${dataKey}`));
                return;
            }

            setTimeout(check, 200);
        };
        check();
    });
};

/**
 * Shortcut: Wait for STOP data.
 * @param {number} timeoutMs
 * @returns {Promise<object>}
 */
window.waitForSTOP = function (timeoutMs = 15000) {
    return window.waitForData('STATE_DATA', timeoutMs);
};

/**
 * Shortcut: Wait for CEAD data.
 * @param {number} timeoutMs
 * @returns {Promise<object>}
 */
window.waitForCEAD = function (timeoutMs = 15000) {
    return window.waitForData('STATE_DATA_CEAD', timeoutMs);
};

/**
 * Shortcut: Wait for STOP + COMUNAS_DATA (vistas comparativas 16, 17).
 * @param {number} timeoutMs
 * @returns {Promise<{stop: object, comunas: Array}>}
 */
window.waitForComunas = function (timeoutMs = 12000) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const check = () => {
            const sData = window.STATE_DATA;
            const cData = window.COMUNAS_DATA;
            if (sData?.isLoaded && cData && cData.length > 0) {
                resolve({ stop: sData, comunas: cData });
                return;
            }
            if (Date.now() - startTime > timeoutMs) {
                // Resolve false instead of rejecting for backward compat with vista16/17 pattern
                resolve(false);
                return;
            }
            setTimeout(check, 200);
        };
        check();
    });
};

/**
 * Shortcut: Wait for both STOP and CEAD data (vistas híbridas).
 * @param {number} timeoutMs
 * @returns {Promise<{stop: object, cead: object}>}
 */
window.waitForBoth = function (timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const check = () => {
            const stop = window.STATE_DATA;
            const cead = window.STATE_DATA_CEAD;
            if (stop?.isLoaded && cead?.isLoaded) {
                resolve({ stop, cead });
                return;
            }
            if (Date.now() - startTime > timeoutMs) {
                reject(new Error('Timeout waiting for STOP + CEAD'));
                return;
            }
            setTimeout(check, 200);
        };
        check();
    });
};

LOG.info("✅ Waiter Utility Loaded (centralized, with timeout protection)");
