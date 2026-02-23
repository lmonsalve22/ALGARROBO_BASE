/**
 * RID Simulator - Core Namespace definition
 * P0: Global State Pollution mitigation.
 */
window.RID = window.RID || {
    // Core Modules placeholders
    State: null,      // Replaces STATE_DATA (Legacy alias kept)
    DataManager: null, // Replaces DataManager
    IA: null,         // Replaces IAModule/IAModuleV2
    UI: null,         // New UI Helper
    Config: {}        // Central config
};

console.log("🚀 RID Core Initialized");
