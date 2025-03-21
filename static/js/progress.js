/**
 * Progress tracking JavaScript for DorkRecon
 */

/**
 * Start progress polling for a scan session
 * @param {number} sessionId - The session ID to track
 * @param {function} onProgress - Callback function for progress updates
 * @param {function} onComplete - Callback function when scan completes
 * @param {function} onError - Callback function for errors
 * @returns {Object} - Controller with stop method
 */
function trackScanProgress(sessionId, onProgress, onComplete, onError) {
    let isRunning = true;
    let pollCount = 0;
    const maxPolls = 600; // 10 minutes at 1 second intervals
    
    // Poll the progress endpoint
    const poll = () => {
        if (!isRunning || pollCount >= maxPolls) {
            return;
        }
        
        pollCount++;
        
        fetch(`/api/scan/progress/${sessionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Progress update:', data);
                
                // Call the progress callback
                if (onProgress) {
                    onProgress(data);
                }
                
                // Check if scan is complete or failed
                if (data.status === 'completed') {
                    isRunning = false;
                    if (onComplete) {
                        onComplete(sessionId);
                    }
                } else if (data.status === 'failed') {
                    isRunning = false;
                    if (onError) {
                        onError(new Error(data.current_step));
                    }
                } else {
                    // Continue polling after 1 second
                    setTimeout(poll, 1000);
                }
            })
            .catch(error => {
                console.error('Error fetching progress:', error);
                
                // Continue polling after a short delay, even on error
                if (isRunning) {
                    setTimeout(poll, 2000);
                }
                
                if (onError) {
                    onError(error);
                }
            });
    };
    
    // Start polling
    poll();
    
    // Return controller object with stop method
    return {
        stop: () => {
            isRunning = false;
        }
    };
}

/**
 * Create and show a progress modal
 * @param {number} sessionId - The session ID to track
 * @param {function} onComplete - Callback function when scan completes
 */
function showProgressModal(sessionId, onComplete) {
    // Create modal element if it doesn't exist
    let progressModal = document.getElementById('progress-modal');
    
    if (!progressModal) {
        const modalElement = document.createElement('div');
        modalElement.id = 'progress-modal';
        modalElement.className = 'modal fade';
        modalElement.tabIndex = -1;
        modalElement.setAttribute('aria-labelledby', 'progress-modal-label');
        modalElement.setAttribute('aria-hidden', 'true');
        modalElement.setAttribute('data-bs-backdrop', 'static');
        modalElement.setAttribute('data-bs-keyboard', 'false');
        
        modalElement.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="progress-modal-label">Scan in Progress</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span id="progress-status">Initializing scan...</span>
                                <span id="progress-percentage">0%</span>
                            </div>
                            <div class="progress">
                                <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <h6>Current Step:</h6>
                            <p id="current-step" class="text-muted">Initializing...</p>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Google Dorks</h6>
                                        <p class="card-text">
                                            <span id="google-dorks-count">0/0</span> completed
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">GitHub Dorks</h6>
                                        <p class="card-text">
                                            <span id="github-dorks-count">0/0</span> completed
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalElement);
        progressModal = modalElement;
    }
    
    // Initialize the Bootstrap modal
    const modal = new bootstrap.Modal(progressModal);
    
    // Show the modal
    modal.show();
    
    // Start tracking progress
    const progressController = trackScanProgress(
        sessionId,
        (data) => {
            // Update progress bar
            const progressBar = document.getElementById('progress-bar');
            const progressPercentage = document.getElementById('progress-percentage');
            const progressStatus = document.getElementById('progress-status');
            const currentStep = document.getElementById('current-step');
            const googleDorksCount = document.getElementById('google-dorks-count');
            const githubDorksCount = document.getElementById('github-dorks-count');
            
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
            }
            
            if (progressPercentage) {
                progressPercentage.textContent = `${data.progress}%`;
            }
            
            if (progressStatus) {
                progressStatus.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                
                // Update status color
                if (data.status === 'running') {
                    progressStatus.className = 'text-primary';
                } else if (data.status === 'completed') {
                    progressStatus.className = 'text-success';
                } else if (data.status === 'failed') {
                    progressStatus.className = 'text-danger';
                }
            }
            
            if (currentStep) {
                currentStep.textContent = data.current_step;
            }
            
            if (googleDorksCount && data.details && data.details.google_dorks) {
                googleDorksCount.textContent = `${data.details.google_dorks.completed}/${data.details.google_dorks.total}`;
            }
            
            if (githubDorksCount && data.details && data.details.github_dorks) {
                githubDorksCount.textContent = `${data.details.github_dorks.completed}/${data.details.github_dorks.total}`;
            }
            
            // If completed, update UI and call complete callback
            if (data.status === 'completed') {
                if (progressBar) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.classList.remove('progress-bar-striped');
                    progressBar.classList.add('bg-success');
                }
                
                if (currentStep) {
                    currentStep.textContent = 'Scan completed successfully!';
                }
            }
            
            // If failed, update UI and show error
            if (data.status === 'failed') {
                if (progressBar) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.classList.remove('progress-bar-striped');
                    progressBar.classList.add('bg-danger');
                }
                
                if (currentStep) {
                    currentStep.textContent = data.current_step;
                    currentStep.className = 'text-danger';
                }
            }
        },
        (sessionId) => {
            // Let the modal stay open for a bit so the user can see the completion
            setTimeout(() => {
                if (onComplete) {
                    onComplete(sessionId);
                }
            }, 1500);
        },
        (error) => {
            console.error('Error tracking progress:', error);
            
            // Update UI to show error
            const progressBar = document.getElementById('progress-bar');
            const progressStatus = document.getElementById('progress-status');
            const currentStep = document.getElementById('current-step');
            
            if (progressBar) {
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.remove('progress-bar-striped');
                progressBar.classList.add('bg-danger');
            }
            
            if (progressStatus) {
                progressStatus.textContent = 'Error';
                progressStatus.className = 'text-danger';
            }
            
            if (currentStep) {
                currentStep.textContent = `Error: ${error.message}`;
                currentStep.className = 'text-danger';
            }
        }
    );
    
    // Stop tracking when modal is closed
    progressModal.addEventListener('hidden.bs.modal', () => {
        progressController.stop();
    });
}