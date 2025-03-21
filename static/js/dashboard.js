/**
 * Dashboard JavaScript for DorkRecon application
 */

// Dashboard state variables
let currentSessionId = null;
let resultsTable = null;
let allResults = [];
let activeFilters = {
    platform: 'all',
    category: 'all',
    severity: 'all',
    search: ''
};

// Initialize the dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if there's a session parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');
    
    // Initialize the sessions table
    initializeSessionsTable();
    
    // If a session ID is provided, load that session
    if (sessionId) {
        loadSession(sessionId);
    }
    
    // Initialize export buttons
    initializeExportButtons();
    
    // Initialize filter controls events
    initializeFilterEvents();
});

/**
 * Initialize the sessions table
 */
function initializeSessionsTable() {
    const tableElement = document.getElementById('sessions-table');
    if (!tableElement) return;
    
    // Load sessions data
    fetch('/api/sessions')
        .then(response => response.json())
        .then(data => {
            // Create sessions table
            const sessionsTable = new DataTable('#sessions-table', {
                data: data.sessions,
                columns: [
                    { 
                        data: 'id',
                        title: 'ID',
                        width: '5%'
                    },
                    { 
                        data: 'target',
                        title: 'Target',
                        width: '25%'
                    },
                    { 
                        data: 'platforms',
                        title: 'Platforms',
                        width: '15%',
                        render: function(data) {
                            if (data === 'both') {
                                return '<span class="badge bg-info">Google & GitHub</span>';
                            } else if (data === 'google') {
                                return '<span class="badge bg-primary">Google</span>';
                            } else {
                                return '<span class="badge bg-success">GitHub</span>';
                            }
                        }
                    },
                    { 
                        data: 'status',
                        title: 'Status',
                        width: '10%',
                        render: function(data) {
                            let badgeClass = 'bg-secondary';
                            if (data === 'completed') {
                                badgeClass = 'bg-success';
                            } else if (data === 'running') {
                                badgeClass = 'bg-primary';
                            } else if (data === 'failed') {
                                badgeClass = 'bg-danger';
                            }
                            return `<span class="badge ${badgeClass}">${data}</span>`;
                        }
                    },
                    { 
                        data: 'results_count',
                        title: 'Results',
                        width: '10%'
                    },
                    { 
                        data: 'created_at',
                        title: 'Date',
                        width: '20%',
                        render: function(data) {
                            return new Date(data).toLocaleString();
                        }
                    },
                    {
                        data: 'id',
                        title: 'Actions',
                        width: '15%',
                        render: function(data) {
                            return `
                                <button class="btn btn-sm btn-primary view-session" data-session-id="${data}">
                                    View
                                </button>
                            `;
                        }
                    }
                ],
                order: [[0, 'desc']],
                pageLength: 10,
                responsive: true
            });
            
            // Add click event for view buttons
            $('#sessions-table').on('click', '.view-session', function() {
                const sessionId = $(this).data('session-id');
                loadSession(sessionId);
            });
        })
        .catch(error => {
            console.error('Error loading sessions:', error);
            document.getElementById('sessions-container').innerHTML = `
                <div class="alert alert-danger">
                    Error loading sessions: ${error.message}
                </div>
            `;
        });
}

/**
 * Load session data
 * @param {number} sessionId - The session ID to load
 */
function loadSession(sessionId) {
    // Update current session ID
    currentSessionId = sessionId;
    
    // Clear active filters
    resetFilters();
    
    // Show loading indicator
    document.getElementById('results-container').innerHTML = `
        <div class="d-flex justify-content-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Show results section
    document.getElementById('results-section').classList.remove('d-none');
    
    // Scroll to results section
    document.getElementById('results-section').scrollIntoView({
        behavior: 'smooth'
    });
    
    // Fetch session data
    fetch(`/api/session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            // Store all results globally
            allResults = data.results;
            
            // Update session info
            updateSessionInfo(data.session);
            
            // Update results table
            updateResultsTable(data.results);
        })
        .catch(error => {
            console.error('Error loading session:', error);
            document.getElementById('results-container').innerHTML = `
                <div class="alert alert-danger">
                    Error loading session data: ${error.message}
                </div>
            `;
            
            // Hide filter controls
            document.getElementById('filter-controls').classList.add('d-none');
            document.getElementById('active-filters').classList.add('d-none');
        });
}

/**
 * Update session information
 * @param {Object} session - The session data
 */
function updateSessionInfo(session) {
    const sessionInfoContainer = document.getElementById('session-info');
    if (!sessionInfoContainer) return;
    
    // Calculate duration
    let duration = 'N/A';
    if (session.completed_at && session.created_at) {
        const start = new Date(session.created_at);
        const end = new Date(session.completed_at);
        const durationMs = end - start;
        const durationSec = Math.round(durationMs / 1000);
        
        if (durationSec < 60) {
            duration = `${durationSec} seconds`;
        } else {
            const minutes = Math.floor(durationSec / 60);
            const seconds = durationSec % 60;
            duration = `${minutes} min ${seconds} sec`;
        }
    }
    
    // Create status badge
    let statusBadge = `<span class="badge bg-secondary">${session.status}</span>`;
    if (session.status === 'completed') {
        statusBadge = '<span class="badge bg-success">Completed</span>';
    } else if (session.status === 'running') {
        statusBadge = '<span class="badge bg-primary">Running</span>';
    } else if (session.status === 'failed') {
        statusBadge = '<span class="badge bg-danger">Failed</span>';
    }
    
    // Format platforms
    let platforms = 'Google & GitHub';
    if (session.platforms === 'google') {
        platforms = 'Google';
    } else if (session.platforms === 'github') {
        platforms = 'GitHub';
    }
    
    // Update container
    // Calculate severity counts
    const highCount = allResults.filter(r => r.severity === 'high' && !r.is_false_positive).length;
    const mediumCount = allResults.filter(r => r.severity === 'medium' && !r.is_false_positive).length;
    const lowCount = allResults.filter(r => r.severity === 'low' && !r.is_false_positive).length;
    const falsePositiveCount = allResults.filter(r => r.is_false_positive).length;
    
    sessionInfoContainer.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    Scan Results: ${session.target}
                    ${statusBadge}
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Target:</strong> ${session.target}</p>
                        <p><strong>Type:</strong> ${session.target_type === 'domain' ? 'Domain' : 'Organization'}</p>
                        <p><strong>Platforms:</strong> ${platforms}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Started:</strong> ${new Date(session.created_at).toLocaleString()}</p>
                        <p><strong>Duration:</strong> ${duration}</p>
                        <p><strong>Results:</strong> ${session.results_count}</p>
                    </div>
                </div>
                
                <!-- Severity summary -->
                <div class="mt-4">
                    <h6>Finding Severity Summary</h6>
                    <div class="severity-summary">
                        <div class="severity-count">
                            <span class="severity-count-number text-danger">${highCount}</span>
                            <span class="severity-count-label">High</span>
                        </div>
                        <div class="severity-count">
                            <span class="severity-count-number text-warning">${mediumCount}</span>
                            <span class="severity-count-label">Medium</span>
                        </div>
                        <div class="severity-count">
                            <span class="severity-count-number text-info">${lowCount}</span>
                            <span class="severity-count-label">Low</span>
                        </div>
                        <div class="severity-count">
                            <span class="severity-count-number text-secondary">${falsePositiveCount}</span>
                            <span class="severity-count-label">False +</span>
                        </div>
                    </div>
                </div>
                
                ${session.error_message ? `
                    <div class="alert alert-danger mt-3">
                        <strong>Error:</strong> ${session.error_message}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Update export buttons
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.disabled = session.results_count === 0;
        btn.setAttribute('data-session-id', session.id);
    });
}

/**
 * Initialize filter events
 */
function initializeFilterEvents() {
    // Platform filter change
    document.getElementById('platform-filter')?.addEventListener('change', function() {
        activeFilters.platform = this.value;
        applyFilters();
        updateActiveFilterTags();
    });
    
    // Category filter change
    document.getElementById('category-filter')?.addEventListener('change', function() {
        activeFilters.category = this.value;
        applyFilters();
        updateActiveFilterTags();
    });
    
    // Severity filter change
    document.getElementById('severity-filter')?.addEventListener('change', function() {
        activeFilters.severity = this.value;
        applyFilters();
        updateActiveFilterTags();
    });
    
    // Search button click
    document.getElementById('search-button')?.addEventListener('click', function() {
        activeFilters.search = document.getElementById('search-input').value.trim();
        applyFilters();
        updateActiveFilterTags();
    });
    
    // Search input enter key
    document.getElementById('search-input')?.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            activeFilters.search = this.value.trim();
            applyFilters();
            updateActiveFilterTags();
        }
    });
    
    // Clear filters button
    document.getElementById('clear-filters-btn')?.addEventListener('click', function() {
        resetFilters();
        applyFilters();
        updateActiveFilterTags();
    });
}

/**
 * Reset all filters to default values
 */
function resetFilters() {
    activeFilters = {
        platform: 'all',
        category: 'all',
        severity: 'all',
        search: ''
    };
    
    // Reset UI elements
    if (document.getElementById('platform-filter')) {
        document.getElementById('platform-filter').value = 'all';
    }
    
    if (document.getElementById('category-filter')) {
        document.getElementById('category-filter').value = 'all';
    }
    
    if (document.getElementById('severity-filter')) {
        document.getElementById('severity-filter').value = 'all';
    }
    
    if (document.getElementById('search-input')) {
        document.getElementById('search-input').value = '';
    }
    
    // Hide active filters
    document.getElementById('active-filters').classList.add('d-none');
}

/**
 * Apply current filters to the results table
 */
function applyFilters() {
    if (!resultsTable) return;
    
    // Create a combined filter function based on active filters
    const filteredData = allResults.filter(result => {
        // Platform filter
        if (activeFilters.platform !== 'all' && result.platform !== activeFilters.platform) {
            return false;
        }
        
        // Category filter
        if (activeFilters.category !== 'all' && result.category !== activeFilters.category) {
            return false;
        }
        
        // Severity filter
        if (activeFilters.severity !== 'all') {
            if (activeFilters.severity === 'false_positive') {
                if (!result.is_false_positive) {
                    return false;
                }
            } else if (result.is_false_positive || result.severity !== activeFilters.severity) {
                return false;
            }
        }
        
        // Search filter
        if (activeFilters.search) {
            const searchTerm = activeFilters.search.toLowerCase();
            const inDork = result.dork.toLowerCase().includes(searchTerm);
            const inUrl = result.result_url.toLowerCase().includes(searchTerm);
            const inSnippet = result.snippet ? result.snippet.toLowerCase().includes(searchTerm) : false;
            
            if (!inDork && !inUrl && !inSnippet) {
                return false;
            }
        }
        
        return true;
    });
    
    // Update the table with filtered data
    resultsTable.clear().rows.add(filteredData).draw();
    
    // Update the results count
    const resultsCountElem = document.getElementById('filtered-results-count');
    if (resultsCountElem) {
        resultsCountElem.textContent = filteredData.length;
        document.getElementById('total-results-count').textContent = allResults.length;
    }
}

/**
 * Update active filter tags display
 */
function updateActiveFilterTags() {
    const activeFiltersContainer = document.getElementById('active-filters');
    const tagsContainer = document.getElementById('active-filter-tags');
    if (!activeFiltersContainer || !tagsContainer) return;
    
    // Clear current tags
    tagsContainer.innerHTML = '';
    
    let hasActiveFilters = false;
    
    // Platform filter tag
    if (activeFilters.platform !== 'all') {
        hasActiveFilters = true;
        addFilterTag(tagsContainer, 'Platform', activeFilters.platform, () => {
            document.getElementById('platform-filter').value = 'all';
            activeFilters.platform = 'all';
            applyFilters();
            updateActiveFilterTags();
        });
    }
    
    // Category filter tag
    if (activeFilters.category !== 'all') {
        hasActiveFilters = true;
        addFilterTag(tagsContainer, 'Category', activeFilters.category, () => {
            document.getElementById('category-filter').value = 'all';
            activeFilters.category = 'all';
            applyFilters();
            updateActiveFilterTags();
        });
    }
    
    // Severity filter tag
    if (activeFilters.severity !== 'all') {
        hasActiveFilters = true;
        let displayName = activeFilters.severity;
        if (displayName === 'false_positive') {
            displayName = 'False Positives';
        } else {
            displayName = displayName.charAt(0).toUpperCase() + displayName.slice(1);
        }
        
        addFilterTag(tagsContainer, 'Severity', displayName, () => {
            document.getElementById('severity-filter').value = 'all';
            activeFilters.severity = 'all';
            applyFilters();
            updateActiveFilterTags();
        });
    }
    
    // Search filter tag
    if (activeFilters.search) {
        hasActiveFilters = true;
        addFilterTag(tagsContainer, 'Search', activeFilters.search, () => {
            document.getElementById('search-input').value = '';
            activeFilters.search = '';
            applyFilters();
            updateActiveFilterTags();
        });
    }
    
    // Show/hide the active filters section
    if (hasActiveFilters) {
        activeFiltersContainer.classList.remove('d-none');
    } else {
        activeFiltersContainer.classList.add('d-none');
    }
}

/**
 * Add a filter tag to the container
 * @param {HTMLElement} container - The container to add the tag to
 * @param {string} type - The filter type
 * @param {string} value - The filter value
 * @param {function} removeCallback - Function to call when removing the tag
 */
function addFilterTag(container, type, value, removeCallback) {
    const tag = document.createElement('div');
    tag.className = 'badge bg-info text-dark p-2 d-flex align-items-center';
    tag.innerHTML = `
        <span><strong>${type}:</strong> ${value}</span>
        <button type="button" class="btn-close btn-close-white ms-2" aria-label="Remove filter"></button>
    `;
    
    const closeButton = tag.querySelector('.btn-close');
    closeButton.addEventListener('click', removeCallback);
    
    container.appendChild(tag);
}

/**
 * Update results table
 * @param {Array} results - The results data
 */
function updateResultsTable(results) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;
    
    // If no results, show message
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="alert alert-info">
                No results found for this scan.
            </div>
        `;
        document.getElementById('filter-controls').classList.add('d-none');
        document.getElementById('active-filters').classList.add('d-none');
        return;
    }
    
    // Create severity summary
    const severityCounts = {
        high: results.filter(r => r.severity === 'high' && !r.is_false_positive).length,
        medium: results.filter(r => r.severity === 'medium' && !r.is_false_positive).length,
        low: results.filter(r => r.severity === 'low' && !r.is_false_positive).length,
        falsePositive: results.filter(r => r.is_false_positive).length
    };
    
    // Create table element
    resultsContainer.innerHTML = `
        <div class="severity-summary mb-4">
            <div class="severity-count">
                <div class="severity-count-number text-danger">${severityCounts.high}</div>
                <div class="severity-count-label">High</div>
            </div>
            <div class="severity-count">
                <div class="severity-count-number text-warning">${severityCounts.medium}</div>
                <div class="severity-count-label">Medium</div>
            </div>
            <div class="severity-count">
                <div class="severity-count-number text-info">${severityCounts.low}</div>
                <div class="severity-count-label">Low</div>
            </div>
            <div class="severity-count">
                <div class="severity-count-number text-secondary">${severityCounts.falsePositive}</div>
                <div class="severity-count-label">False Positive</div>
            </div>
        </div>
        <div class="mb-3">
            <span class="text-muted">Showing <span id="filtered-results-count">${results.length}</span> of <span id="total-results-count">${results.length}</span> results</span>
        </div>
        <div class="table-responsive">
            <table id="results-table" class="table table-striped table-hover" style="width:100%">
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Platform</th>
                        <th>Category</th>
                        <th>Dork</th>
                        <th>Result</th>
                        <th>Snippet</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                </tbody>
            </table>
        </div>
    `;
    
    // Show filter controls
    document.getElementById('filter-controls').classList.remove('d-none');
    
    // Initialize DataTable
    if (resultsTable) {
        resultsTable.destroy();
    }
    
    resultsTable = new DataTable('#results-table', {
        data: results,
        columns: [
            { 
                data: 'severity',
                title: 'Severity',
                width: '8%',
                render: function(data, type, row) {
                    if (row.is_false_positive) {
                        return '<span class="false-positive-badge">False +</span>';
                    }
                    
                    const severityClass = 'severity-' + data.toLowerCase();
                    return `<span class="severity-indicator ${severityClass}">${data}</span>`;
                }
            },
            { 
                data: 'platform',
                title: 'Platform',
                width: '8%',
                render: function(data) {
                    if (data === 'google') {
                        return '<span class="badge bg-primary">Google</span>';
                    } else {
                        return '<span class="badge bg-success">GitHub</span>';
                    }
                }
            },
            { 
                data: 'category',
                title: 'Category',
                width: '12%'
            },
            { 
                data: 'dork',
                title: 'Dork',
                width: '20%'
            },
            { 
                data: 'result_url',
                title: 'Result',
                width: '20%',
                render: function(data) {
                    return `<a href="${data}" target="_blank" rel="noopener noreferrer">${truncateString(data, 40)}</a>`;
                }
            },
            { 
                data: 'snippet',
                title: 'Snippet',
                width: '22%',
                render: function(data) {
                    return `<div class="text-truncate" style="max-width: 300px;" title="${data ? escapeHtml(data) : ''}">${truncateString(data, 50)}</div>`;
                }
            },
            {
                data: 'id',
                title: 'Actions',
                width: '10%',
                render: function(data, type, row) {
                    // Mark false positive button
                    const fpClass = row.is_false_positive ? 'btn-secondary' : 'btn-outline-secondary';
                    const fpIcon = row.is_false_positive ? 'check-circle' : 'circle';
                    const fpTitle = row.is_false_positive ? 'Marked as False Positive' : 'Mark as False Positive';
                    
                    // Severity dropdown
                    const severityOptions = {
                        high: row.severity === 'high' ? 'selected' : '',
                        medium: row.severity === 'medium' ? 'selected' : '',
                        low: row.severity === 'low' ? 'selected' : ''
                    };
                    
                    return `
                    <div class="result-actions">
                        <button class="btn btn-sm ${fpClass} toggle-false-positive" data-result-id="${data}" title="${fpTitle}">
                            <i class="bi bi-${fpIcon}"></i>
                        </button>
                        <select class="form-select form-select-sm change-severity" data-result-id="${data}">
                            <option value="high" ${severityOptions.high}>High</option>
                            <option value="medium" ${severityOptions.medium}>Medium</option>
                            <option value="low" ${severityOptions.low}>Low</option>
                        </select>
                    </div>
                    `;
                }
            }
        ],
        order: [[0, 'asc'], [1, 'asc']],
        pageLength: 25,
        responsive: true
    });
    
    // Populate category filter
    populateCategoryFilter(results);
    
    // Create quick filter tags
    createQuickFilterTags(results);
    
    // Add event listeners for false positive marking
    document.querySelectorAll('.toggle-false-positive').forEach(button => {
        button.addEventListener('click', function() {
            const resultId = this.getAttribute('data-result-id');
            const currentState = this.classList.contains('btn-secondary');
            
            // Toggle the false positive state
            markAsFalsePositive(resultId, !currentState);
        });
    });
    
    // Add event listeners for severity changes
    document.querySelectorAll('.change-severity').forEach(select => {
        select.addEventListener('change', function() {
            const resultId = this.getAttribute('data-result-id');
            const newSeverity = this.value;
            
            // Update the severity
            updateSeverity(resultId, newSeverity);
        });
    });
}

/**
 * Mark a result as a false positive
 * @param {number} resultId - The result ID
 * @param {boolean} isFalsePositive - Whether to mark as false positive
 */
function markAsFalsePositive(resultId, isFalsePositive) {
    // Default notes
    const notes = isFalsePositive ? 'Marked as false positive by user.' : '';
    
    // API call to mark as false positive
    fetch(`/api/result/${resultId}/false_positive`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            is_false_positive: isFalsePositive,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.is_false_positive !== undefined) {
            // Update the result in the local data
            const resultIndex = allResults.findIndex(r => r.id == resultId);
            if (resultIndex >= 0) {
                allResults[resultIndex].is_false_positive = data.is_false_positive;
                allResults[resultIndex].notes = data.notes;
                
                // Reload the current session to refresh the UI
                loadSession(currentSessionId);
            }
        }
    })
    .catch(error => {
        console.error('Error updating false positive status:', error);
        alert('Error updating false positive status. Please try again.');
    });
}

/**
 * Update a result's severity
 * @param {number} resultId - The result ID
 * @param {string} severity - The new severity level
 */
function updateSeverity(resultId, severity) {
    // API call to update severity
    fetch(`/api/result/${resultId}/severity`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            severity: severity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.severity) {
            // Update the result in the local data
            const resultIndex = allResults.findIndex(r => r.id == resultId);
            if (resultIndex >= 0) {
                allResults[resultIndex].severity = data.severity;
                
                // Reload the current session to refresh the UI
                loadSession(currentSessionId);
            }
        }
    })
    .catch(error => {
        console.error('Error updating severity:', error);
        alert('Error updating severity. Please try again.');
    });
}

/**
 * Populate category filter dropdown
 * @param {Array} results - The results data
 */
function populateCategoryFilter(results) {
    const categoryFilter = document.getElementById('category-filter');
    if (!categoryFilter) return;
    
    // Get unique categories
    const categories = [...new Set(results.map(r => r.category))];
    
    // Clear existing options except the first "All Categories" option
    while (categoryFilter.options.length > 1) {
        categoryFilter.remove(1);
    }
    
    // Add options for each category
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });
}

/**
 * Create quick filter tags
 * @param {Array} results - The results data
 */
function createQuickFilterTags(results) {
    const tagsContainer = document.getElementById('quick-tags-container');
    if (!tagsContainer) return;
    
    // Clear existing tags
    tagsContainer.innerHTML = '';
    
    // Common filter terms for security researchers
    const commonTerms = [
        'password', 'secret', 'config', 'api', 'key', 'token', 'admin',
        'sql', 'database', 'credentials', 'backup', '.git', 'login'
    ];
    
    // Create tags
    commonTerms.forEach(term => {
        const tag = document.createElement('button');
        tag.className = 'btn btn-sm btn-outline-secondary';
        tag.textContent = term;
        tag.addEventListener('click', () => {
            document.getElementById('search-input').value = term;
            activeFilters.search = term;
            applyFilters();
            updateActiveFilterTags();
        });
        tagsContainer.appendChild(tag);
    });
}

/**
 * Initialize export buttons
 */
function initializeExportButtons() {
    document.querySelectorAll('.export-btn').forEach(button => {
        button.addEventListener('click', function() {
            const sessionId = this.getAttribute('data-session-id');
            const format = this.getAttribute('data-format');
            
            if (!sessionId || !format) {
                console.error('Missing session ID or format for export');
                return;
            }
            
            // Download export file
            window.location.href = `/api/export/session/${sessionId}/${format}`;
        });
    });
}

/**
 * Helper function to truncate a string
 * @param {string} str - The string to truncate
 * @param {number} maxLength - The maximum length
 * @returns {string} The truncated string
 */
function truncateString(str, maxLength) {
    if (!str) return '';
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

/**
 * Helper function to escape HTML
 * @param {string} html - The HTML to escape
 * @returns {string} The escaped HTML
 */
function escapeHtml(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}