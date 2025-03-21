/**
 * Exports JavaScript for DorkRecon application
 */

/**
 * Export session results as CSV
 * @param {number} sessionId - The session ID to export
 */
function exportCsv(sessionId) {
    if (!sessionId) {
        console.error('No session ID provided for CSV export');
        return;
    }
    
    // Download CSV file
    window.location.href = `/api/export/session/${sessionId}/csv`;
}

/**
 * Export session results as JSON
 * @param {number} sessionId - The session ID to export
 */
function exportJson(sessionId) {
    if (!sessionId) {
        console.error('No session ID provided for JSON export');
        return;
    }
    
    // Download JSON file
    window.location.href = `/api/export/session/${sessionId}/json`;
}

/**
 * Generate a sanitized filename for exports
 * @param {string} prefix - The prefix for the filename
 * @param {string} target - The target domain or organization
 * @returns {string} The sanitized filename
 */
function generateFilename(prefix, target) {
    // Sanitize target for filename
    const sanitizedTarget = target.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    return `${prefix}_${sanitizedTarget}_${timestamp}`;
}
