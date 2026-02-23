/**
 * RID View Controller
 * Centralizes the view initialization pattern to eliminate boilerplate duplication
 * across all vistaX.html files.
 *
 * Usage (in any vistaX.html):
 *   RID.View.init(async (S, C) => {
 *       // Your view logic here
 *   });
 */
(function () {
    window.RID = window.RID || {};

    window.RID.View = {
        /**
         * Waits for STATE_DATA to be ready, then executes the provided callback.
         * Handles errors gracefully and avoids race conditions.
         *
         * @param {function(S: object, C: object): Promise<void>} callback - Async function receiving STATE_DATA and COLS.
         * @param {object} [options]
         * @param {string} [options.source='stop'] - Data source: 'stop' or 'cead'.
         */
        init(callback, options = {}) {
            const source = options.source || 'stop';

            const waitForData = () => new Promise((resolve, reject) => {
                let attempts = 0;
                const MAX_ATTEMPTS = 150; // 15 seconds timeout

                const check = () => {
                    attempts++;
                    if (attempts > MAX_ATTEMPTS) {
                        reject(new Error('RID.View: Timeout waiting for data. DataManager may have failed.'));
                        return;
                    }

                    const isStopReady = source === 'stop' && window.STATE_DATA?.isLoaded;
                    const isCeadReady = source === 'cead' && window.STATE_DATA_CEAD?.isLoaded;

                    if (isStopReady || isCeadReady) {
                        resolve();
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            });

            (async () => {
                try {
                    await waitForData();

                    const S = source === 'cead' ? window.STATE_DATA_CEAD : window.STATE_DATA;
                    const C = source === 'cead' ? window.COLS_CEAD : window.COLS;

                    await callback(S, C);
                } catch (err) {
                    console.error('❌ RID.View.init error:', err);
                }
            })();
        }
    };

    console.log('✅ RID.View Controller loaded.');
})();
