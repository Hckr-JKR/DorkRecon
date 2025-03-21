/**
 * Main JavaScript file for DorkRecon application
 */

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Initialize form submission for the dork scan form
    initializeScanForm();

    // Initialize categories checkboxes
    initializeCategories();
});

/**
 * Initialize the scan form submission
 */
function initializeScanForm() {
    const scanForm = document.getElementById('scan-form');
    if (!scanForm) return;

    scanForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const target = document.getElementById('target').value.trim();
        
        // Get selected platforms
        const platformRadios = document.querySelectorAll('input[name="platform"]');
        let platforms = 'both';
        for (const radio of platformRadios) {
            if (radio.checked) {
                platforms = radio.value;
                break;
            }
        }
        
        // Get selected categories
        const categoryCheckboxes = document.querySelectorAll('.category-checkbox:checked');
        const categories = Array.from(categoryCheckboxes).map(cb => cb.value);
        
        // Validate input
        if (!target) {
            showAlert('Please enter a target domain or organization', 'danger');
            return;
        }
        
        // Disable form and show loading indicator
        const submitButton = scanForm.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning...';
        
        // Show scan status container
        const scanStatusContainer = document.getElementById('scan-status-container');
        if (scanStatusContainer) {
            scanStatusContainer.classList.remove('d-none');
            scanStatusContainer.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        <span>Starting scan for <strong>${target}</strong>...</span>
                    </div>
                </div>
            `;
        }
        
        // Prepare data for API request
        const requestData = {
            target: target,
            platforms: platforms,
            categories: categories
        };
        
        // Make API request to start scan
        fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Scan started successfully:', data);
            
            // Show progress modal
            showProgressModal(data.session_id, (sessionId) => {
                // Redirect to dashboard with session ID after completion
                window.location.href = `/dashboard?session=${sessionId}`;
            });
            
            // Reset button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
            
            // Update scan status
            if (scanStatusContainer) {
                scanStatusContainer.innerHTML = `
                    <div class="alert alert-success">
                        <strong>Success:</strong> Scan started! Track progress in the modal.
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error starting scan:', error);
            
            // Show error alert
            showAlert('Error starting scan: ' + error.message, 'danger');
            
            // Reset button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
            
            // Update scan status
            if (scanStatusContainer) {
                scanStatusContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> ${error.message}
                    </div>
                `;
            }
        });
    });
}

/**
 * Initialize categories checkboxes
 */
function initializeCategories() {
    const platformRadios = document.querySelectorAll('input[name="platform"]');
    if (!platformRadios.length) return;
    
    // Update categories when platform selection changes
    platformRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateCategories(this.value);
        });
    });
    
    // Initialize categories based on default platform
    let selectedPlatform = 'both';
    platformRadios.forEach(radio => {
        if (radio.checked) {
            selectedPlatform = radio.value;
        }
    });
    
    updateCategories(selectedPlatform);
}

/**
 * Update categories based on selected platform
 * @param {string} platform - The selected platform (google, github, or both)
 */
function updateCategories(platform) {
    const categoriesContainer = document.getElementById('categories-container');
    if (!categoriesContainer) return;
    
    // Show loading indicator
    categoriesContainer.innerHTML = `
        <div class="text-center">
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Loading categories...
        </div>
    `;
    
    // Fetch categories from API
    fetch(`/api/categories?platform=${platform}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Create checkboxes for each category
            let html = '<div class="row">';
            
            data.categories.forEach((category, index) => {
                html += `
                    <div class="col-md-6 mb-2">
                        <div class="form-check">
                            <input class="form-check-input category-checkbox" type="checkbox" value="${category}" id="category-${index}" checked>
                            <label class="form-check-label" for="category-${index}">
                                ${category}
                            </label>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            
            // Update categories container
            categoriesContainer.innerHTML = html;
            
            // Add "Select All" / "Deselect All" controls
            const selectAllContainer = document.createElement('div');
            selectAllContainer.className = 'mt-2';
            selectAllContainer.innerHTML = `
                <button type="button" class="btn btn-sm btn-outline-secondary me-2" id="select-all-categories">Select All</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="deselect-all-categories">Deselect All</button>
            `;
            
            categoriesContainer.prepend(selectAllContainer);
            
            // Initialize "Select All" / "Deselect All" buttons
            document.getElementById('select-all-categories').addEventListener('click', function() {
                document.querySelectorAll('.category-checkbox').forEach(cb => {
                    cb.checked = true;
                });
            });
            
            document.getElementById('deselect-all-categories').addEventListener('click', function() {
                document.querySelectorAll('.category-checkbox').forEach(cb => {
                    cb.checked = false;
                });
            });
        })
        .catch(error => {
            console.error('Error fetching categories:', error);
            categoriesContainer.innerHTML = `
                <div class="alert alert-danger">
                    Error loading categories: ${error.message}
                </div>
            `;
        });
}

/**
 * Show an alert message
 * @param {string} message - The message to display
 * @param {string} type - The alert type (success, info, warning, danger)
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertElement);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertElement);
        bsAlert.close();
    }, 5000);
}
