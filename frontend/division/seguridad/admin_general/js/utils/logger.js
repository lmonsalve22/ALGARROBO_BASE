/**
 * SEC-009 Fix: Conditional Logger
 * Suppresses all debug output in production to prevent reconnaissance
 * via browser console (module names, data paths, cache structure).
 *
 * Detection: production if hostname !== 'localhost' / '127.0.0.1'
 * and no ?debug=1 query param.
 *
 * Usage: Replace console.log/warn/error with LOG.info/warn/error
 */
(function () {
    'use strict';

    const host = window.location.hostname;
    const params = new URLSearchParams(window.location.search);
    const IS_DEV = host === 'localhost' || host === '127.0.0.1' || host === '' || params.has('debug');

    const noop = () => { };

    window.LOG = {
        info: IS_DEV ? console.log.bind(console) : noop,
        warn: IS_DEV ? console.warn.bind(console) : noop,
        error: IS_DEV ? console.error.bind(console) : noop,
        debug: IS_DEV ? console.debug.bind(console) : noop,
        /** Always log — use only for critical user-facing errors */
        critical: console.error.bind(console)
    };

    if (IS_DEV) {
        console.log('🔧 Logger: DEV mode (all output enabled)');
    }
})();
