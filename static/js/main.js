// Global variables
let currentJobId = null;
let statusInterval = null;

// DOM elements
const uploadSection = document.getElementById('upload-section');
const processingSection = document.getElementById('processing-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');

const uploadForm = document.getElementById('upload-form');
const uploadArea = document.getElementById('upload-area');
const videoFileInput = document.getElementById('video-file');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileMeta = document.getElementById('file-meta');
const removeFileBtn = document.getElementById('remove-file');
const uploadBtn = document.getElementById('upload-btn');

const progressFill = document.getElementById('progress-fill');
const progressPercentage = document.getElementById('progress-percentage');
const currentStep = document.getElementById('current-step');
const processingDetails = document.getElementById('processing-details');

const resultsContent = document.getElementById('results-content');
const newAnalysisBtn = document.getElementById('new-analysis-btn');
const retryBtn = document.getElementById('retry-btn');
const errorMessage = document.getElementById('error-message');

// Utility functions
function showSection(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    section.classList.add('active');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// File upload handling
uploadArea.addEventListener('click', () => {
    videoFileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        videoFileInput.files = files;
        handleFileSelect();
    }
});

videoFileInput.addEventListener('change', handleFileSelect);

function handleFileSelect() {
    const file = videoFileInput.files[0];
    
    if (!file) {
        hideFileInfo();
        return;
    }
    
    // Validate file type
    if (!file.type.includes('mp4')) {
        alert('Please select an MP4 video file.');
        videoFileInput.value = '';
        hideFileInfo();
        return;
    }
    
    // Show file info
    fileName.textContent = file.name;
    fileMeta.textContent = `${formatFileSize(file.size)}`;
    fileInfo.classList.remove('hidden');
    
    // Check form validity
    checkFormValidity();
}

function hideFileInfo() {
    fileInfo.classList.add('hidden');
    checkFormValidity();
}

removeFileBtn.addEventListener('click', () => {
    videoFileInput.value = '';
    hideFileInfo();
});

function checkFormValidity() {
    const hasFile = videoFileInput.files.length > 0;
    
    uploadBtn.disabled = !hasFile;
}

// Form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('video', videoFileInput.files[0]);
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="btn-text">Uploading...</span><span class="btn-icon">...</span>';
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Upload failed');
        }
        
        // Check if video needs trimming
        if (result.needs_trimming) {
            showTrimDialog(result);
            return;
        }
        
        // Start processing
        currentJobId = result.job_id;
        showProcessing();
        startStatusPolling();
        
    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message);
        resetUploadForm();
    }
});

function resetUploadForm() {
    uploadBtn.disabled = false;
    uploadBtn.innerHTML = '<span class="btn-text">Start Analysis</span><span class="btn-icon">▶</span>';
    checkFormValidity();
}

// Processing status
function showProcessing() {
    showSection(processingSection);
    updateProgress(0, 'Starting analysis...');
    resetProcessingSteps();
}

function updateProgress(percentage, step) {
    progressFill.style.width = `${percentage}%`;
    progressPercentage.textContent = `${percentage}%`;
    currentStep.textContent = step;
    
    // Update processing steps
    updateProcessingSteps(percentage);
    
    // Update processing details
    if (percentage < 25) {
        processingDetails.textContent = 'Scanning video for motion patterns...';
    } else if (percentage < 50) {
        processingDetails.textContent = 'Grouping motion events into analysis windows...';
    } else if (percentage < 80) {
        processingDetails.textContent = 'Analyzing frames with AI for safety concerns...';
    } else {
        processingDetails.textContent = 'Generating detailed analysis report...';
    }
}

function updateProcessingSteps(percentage) {
    const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
    
    steps.forEach((stepId, index) => {
        const stepElement = document.getElementById(stepId);
        const stepPercentage = (index + 1) * 25;
        
        stepElement.classList.remove('active', 'completed');
        
        if (percentage >= stepPercentage) {
            stepElement.classList.add('completed');
        } else if (percentage >= stepPercentage - 25) {
            stepElement.classList.add('active');
        }
    });
}

function resetProcessingSteps() {
    const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
    steps.forEach(stepId => {
        const stepElement = document.getElementById(stepId);
        stepElement.classList.remove('active', 'completed');
    });
}

function startStatusPolling() {
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const status = await response.json();
            
            if (!response.ok) {
                throw new Error(status.error || 'Status check failed');
            }
            
            updateProgress(status.progress, status.current_step);
            
            if (status.status === 'completed') {
                clearInterval(statusInterval);
                showResults(status.result);
            } else if (status.status === 'error') {
                clearInterval(statusInterval);
                showError(status.error || 'Analysis failed');
            }
            
        } catch (error) {
            console.error('Status check error:', error);
            clearInterval(statusInterval);
            showError('Connection lost. Please try again.');
        }
    }, 2000); // Poll every 2 seconds
}

// Results display
function showResults(result) {
    showSection(resultsSection);
    
    const hasIncidents = result.summary.violence_detected;
    
    let html = '';
    
    // Status indicator
    if (hasIncidents) {
        html += `
            <div class="result-status danger">
                🚨 CONCERNING BEHAVIOR DETECTED
            </div>
        `;
    } else {
        html += `
            <div class="result-status safe">
                ✅ NO CONCERNING BEHAVIOR DETECTED
            </div>
        `;
    }
    
    // Summary information
    html += `
        <div class="result-summary">
            <p><strong>Analysis Summary:</strong></p>
            <ul>
                <li>Total sequences analyzed: ${result.analysis_metadata.total_sequences_analyzed}</li>
                <li>Incidents found: ${result.analysis_metadata.violence_incidents_found}</li>
                <li>Highest confidence: ${result.summary.highest_confidence}%</li>
            </ul>
        </div>
    `;
    
    // Incidents details
    if (hasIncidents && result.incidents.length > 0) {
        html += '<div class="incidents-list"><h3>Incident Details:</h3>';
        
        result.incidents.forEach((incident, index) => {
            if (incident.inappropriate_behavior_detected) {
                html += `
                    <div class="incident">
                        <div class="incident-header">
                            <div class="incident-time">
                                📍 ${incident.time_range.start_formatted} - ${incident.time_range.end_formatted}
                            </div>
                            <div class="incident-confidence">
                                ${incident.confidence_percentage}% confidence
                            </div>
                        </div>
                        <div class="incident-description">
                            ${incident.description}
                        </div>
                        ${incident.web_image_path ? `
                            <div class="evidence-frames">
                                <img src="${incident.web_image_path}" alt="Evidence frames" />
                                <div class="frames-caption">
                                    Evidence frames showing detected motion areas (red rectangles)
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            }
        });
        
        html += '</div>';
    }
    
    resultsContent.innerHTML = html;
}

// Trim dialog handling
function showTrimDialog(result) {
    // Create and show trim dialog
    const trimDialog = document.createElement('div');
    trimDialog.className = 'trim-dialog-overlay';
    trimDialog.innerHTML = `
        <div class="trim-dialog">
            <h3>Video Too Long</h3>
            <p>${result.message}</p>
            <div class="video-info">
                <p><strong>Original Duration:</strong> ${result.original_duration.toFixed(1)} seconds</p>
                <p><strong>Will be trimmed to:</strong> 60.0 seconds</p>
            </div>
            <div class="dialog-buttons">
                <button class="btn btn-primary" id="proceed-trim-btn">
                    <span class="btn-text">Analyze First 60 Seconds</span>
                    <span class="btn-icon">✂</span>
                </button>
                <button class="btn btn-secondary" id="cancel-trim-btn">
                    <span class="btn-text">Cancel</span>
                    <span class="btn-icon">X</span>
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(trimDialog);
    
    // Handle proceed button
    document.getElementById('proceed-trim-btn').addEventListener('click', async () => {
        document.body.removeChild(trimDialog);
        await proceedWithTrimming(result);
    });
    
    // Handle cancel button
    document.getElementById('cancel-trim-btn').addEventListener('click', () => {
        document.body.removeChild(trimDialog);
        resetUploadForm();
    });
}

async function proceedWithTrimming(result) {
    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="btn-text">Trimming Video...</span><span class="btn-icon">✂</span>';
        
        const response = await fetch('/trim-and-analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: result.job_id,
                temp_video_path: result.temp_video_path
            })
        });
        
        const trimResult = await response.json();
        
        if (!response.ok) {
            throw new Error(trimResult.error || 'Trimming failed');
        }
        
        // Start processing with trimmed video
        currentJobId = trimResult.job_id;
        showProcessing();
        startStatusPolling();
        
    } catch (error) {
        console.error('Trimming error:', error);
        showError(error.message);
        resetUploadForm();
    }
}

// Error handling
function showError(message) {
    showSection(errorSection);
    errorMessage.textContent = message;
}

// Navigation buttons
newAnalysisBtn.addEventListener('click', () => {
    // Cleanup current job
    if (currentJobId) {
        fetch(`/cleanup/${currentJobId}`, { method: 'POST' }).catch(console.error);
        currentJobId = null;
    }
    
    // Reset form
    uploadForm.reset();
    hideFileInfo();
    resetUploadForm();
    
    // Show upload section
    showSection(uploadSection);
});

retryBtn.addEventListener('click', () => {
    // Cleanup current job
    if (currentJobId) {
        fetch(`/cleanup/${currentJobId}`, { method: 'POST' }).catch(console.error);
        currentJobId = null;
    }
    
    // Show upload section
    showSection(uploadSection);
    resetUploadForm();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (currentJobId) {
        fetch(`/cleanup/${currentJobId}`, { method: 'POST' }).catch(console.error);
    }
});

// Examples functionality
async function loadExamples() {
    try {
        const response = await fetch('/static/examples/examples_data.json');
        const data = await response.json();
        displayExamples(data.examples);
    } catch (error) {
        console.error('Failed to load examples:', error);
    }
}

function displayExamples(examples) {
    const examplesGrid = document.getElementById('examples-grid');
    
    examplesGrid.innerHTML = examples.map(example => `
        <div class="example-card" onclick="showExampleModal('${example.id}')">
            <div class="example-header">
                <div class="example-thumbnail-container">
                    <img src="${example.thumbnail}" alt="${example.title}" class="example-thumbnail">
                    <div class="play-button-overlay"></div>
                </div>
                <div class="example-info">
                    <h4>${example.title}</h4>
                    <span class="example-duration">${example.duration}</span>
                </div>
            </div>
            
            <div class="example-result">
                <span class="result-badge ${example.result.status}">
                    ${example.result.status === 'safe' ? '✓' : '⚠'} ${example.result.status === 'safe' ? 'Safe' : 'Concerning'}
                </span>
                <p class="example-summary">${example.result.summary}</p>
            </div>
            
            <div class="example-stats">
                <span>Confidence: ${example.result.confidence}%</span>
                <span>Sequences: ${example.result.sequences_analyzed}</span>
            </div>
            
            <div class="view-details-btn">
                View Details →
            </div>
        </div>
    `).join('');
}

function showExampleModal(exampleId) {
    fetch('/static/examples/examples_data.json')
        .then(response => response.json())
        .then(data => {
            const example = data.examples.find(ex => ex.id === exampleId);
            if (example) {
                createExampleModal(example);
            }
        })
        .catch(error => console.error('Failed to load example details:', error));
}

function createExampleModal(example) {
    const modal = document.createElement('div');
    modal.className = 'example-modal-overlay';
    modal.innerHTML = `
        <div class="example-modal">
            <div class="modal-header">
                <h3 class="modal-title">${example.title}</h3>
                <button class="modal-close" onclick="closeExampleModal()">&times;</button>
            </div>
            
            <video class="modal-video" controls>
                <source src="${example.videoPath}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            
            <div class="modal-result">
                <span class="result-badge ${example.result.status}">
                    ${example.result.status === 'safe' ? '✓' : '⚠'} ${example.result.status === 'safe' ? 'Safe' : 'Concerning'} 
                    (${example.result.confidence}% confidence)
                </span>
                <p class="modal-details">${example.result.details}</p>
            </div>
            
            <div class="modal-stats">
                <div class="stat-item">
                    <span class="stat-value">${example.result.sequences_analyzed}</span>
                    <span class="stat-label">Sequences</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${example.result.incidents_found}</span>
                    <span class="stat-label">Incidents</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${example.result.confidence}%</span>
                    <span class="stat-label">Confidence</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${example.duration}</span>
                    <span class="stat-label">Duration</span>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeExampleModal();
        }
    });
}

function closeExampleModal() {
    const modal = document.querySelector('.example-modal-overlay');
    if (modal) {
        document.body.removeChild(modal);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkFormValidity();
    loadExamples();
});