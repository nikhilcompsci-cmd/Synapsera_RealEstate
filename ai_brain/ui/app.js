// API Base URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? '/api/v1' 
    : 'http://localhost:8000/api/v1';

// Current selected project ID
let currentProjectId = null;

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    console.log('UI Loaded - Fetching projects...');
    loadProjects();
    
    // Show connection status
    checkServerConnection();
});

// ==================== PROJECT MANAGEMENT ====================

/**
 * Create a new project
 */
async function createProject() {
    const projectName = document.getElementById('projectName').value.trim();
    const resultDiv = document.getElementById('projectCreateResult');
    
    if (!projectName) {
        showError(resultDiv, 'Please enter a project name');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/project`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: projectName })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create project');
        }
        
        const data = await response.json();
        showSuccess(resultDiv, `Project created! ID: ${data.id}`);
        
        // Clear input and reload projects
        document.getElementById('projectName').value = '';
        await loadProjects();
        
        // Auto-select the new project
        document.getElementById('projectSelect').value = data.id;
        currentProjectId = data.id;
        
    } catch (error) {
        console.error('Create project error:', error);
        const errorMsg = error.message || String(error) || 'Failed to create project';
        showError(resultDiv, errorMsg);
    }
}

/**
 * Load all projects into dropdown
 */
async function loadProjects() {
    const selectElement = document.getElementById('projectSelect');
    
    try {
        console.log('Loading projects from:', `${API_BASE}/project`);
        const response = await fetch(`${API_BASE}/project`);
        
        if (!response.ok) {
            throw new Error(`Failed to load projects (${response.status})`);
        }
        
        const projects = await response.json();
        
        // Clear and repopulate dropdown
        selectElement.innerHTML = '<option value="">-- Select a project --</option>';
        
        if (projects.length === 0) {
            console.log('No projects found. Create a new project first.');
            selectElement.innerHTML += '<option value="" disabled>No projects available - create one first</option>';
            return;
        }
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.name} (ID: ${project.id})`;
            selectElement.appendChild(option);
        });
        
        console.log(`Loaded ${projects.length} projects`);
        
    } catch (error) {
        console.error('Error loading projects:', error);
        selectElement.innerHTML = '<option value="">-- Error loading projects --</option>';
        
        // Show error in UI
        const resultDiv = document.getElementById('projectCreateResult');
        if (resultDiv) {
            const errorMsg = error.message || String(error) || 'Unknown error';
            showError(resultDiv, `Failed to load projects: ${errorMsg}. Make sure the server is running at http://localhost:8000`);
        }
    }
}

/**
 * Handle project selection change
 */
function onProjectChange() {
    const selectElement = document.getElementById('projectSelect');
    currentProjectId = selectElement.value ? parseInt(selectElement.value) : null;
    
    if (currentProjectId) {
        console.log(`Selected project ID: ${currentProjectId}`);
        refreshStatus();
    }
}

// ==================== DOCUMENT UPLOAD ====================

/**
 * Upload a document to the selected project
 */
async function uploadDocument() {
    const fileInput = document.getElementById('fileInput');
    const resultDiv = document.getElementById('uploadResult');
    
    if (!currentProjectId) {
        showError(resultDiv, 'Please select a project first');
        return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showError(resultDiv, 'Please select a PDF file');
        return;
    }
    
    const file = fileInput.files[0];
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError(resultDiv, 'Only PDF files are supported');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showInfo(resultDiv, 'Uploading...');
        
        const response = await fetch(`${API_BASE}/project/${currentProjectId}/document/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        showSuccess(resultDiv, `Upload successful! Document ID: ${data.document_id}, Pages: ${data.page_count}, Chunks: ${data.chunk_count}`);
        
        // Clear file input
        fileInput.value = '';
        
        // Refresh status after 2 seconds to allow processing
        setTimeout(() => refreshStatus(), 2000);
        
    } catch (error) {
        console.error('Upload error:', error);
        const errorMsg = error.message || String(error) || 'Upload failed';
        showError(resultDiv, errorMsg);
    }
}

// ==================== INGESTION STATUS ====================

/**
 * Refresh ingestion status for selected project
 */
async function refreshStatus() {
    const statusDiv = document.getElementById('ingestionStatus');
    
    if (!currentProjectId) {
        statusDiv.innerHTML = '<p class="text-gray-400">Please select a project first</p>';
        return;
    }
    
    try {
        showInfo(statusDiv, 'Loading status...');
        
        const response = await fetch(`${API_BASE}/project/${currentProjectId}/ingestion-status`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const data = await response.json();
        
        // Build status HTML
        let html = `
            <div class="space-y-3">
                <div class="grid grid-cols-3 gap-2 text-center">
                    <div class="bg-blue-100 p-2 rounded">
                        <div class="text-2xl font-bold text-blue-700">${data.total_documents}</div>
                        <div class="text-xs text-gray-600">Total Docs</div>
                    </div>
                    <div class="bg-green-100 p-2 rounded">
                        <div class="text-2xl font-bold text-green-700">${data.completed}</div>
                        <div class="text-xs text-gray-600">Completed</div>
                    </div>
                    <div class="bg-yellow-100 p-2 rounded">
                        <div class="text-2xl font-bold text-yellow-700">${data.processing}</div>
                        <div class="text-xs text-gray-600">Processing</div>
                    </div>
                </div>
        `;
        
        if (data.failed > 0) {
            html += `
                <div class="bg-red-100 p-2 rounded text-center">
                    <div class="text-2xl font-bold text-red-700">${data.failed}</div>
                    <div class="text-xs text-gray-600">Failed</div>
                </div>
            `;
        }
        
        // Document list
        if (data.documents && data.documents.length > 0) {
            html += '<div class="mt-4"><h3 class="font-semibold mb-2">Documents:</h3><ul class="space-y-1">';
            
            data.documents.forEach(doc => {
                const statusColor = doc.ingestion_status === 'completed' ? 'green' : 
                                   doc.ingestion_status === 'failed' ? 'red' : 'yellow';
                html += `
                    <li class="text-xs bg-gray-50 p-2 rounded">
                        <div class="font-semibold">ID: ${doc.id} - ${doc.filename}</div>
                        <div class="text-gray-600">
                            Status: <span class="text-${statusColor}-600 font-semibold">${doc.ingestion_status}</span> | 
                            Pages: ${doc.page_count || 'N/A'} | 
                            Chunks: ${doc.chunk_count || 'N/A'}
                        </div>
                    </li>
                `;
            });
            
            html += '</ul></div>';
        }
        
        html += '</div>';
        statusDiv.innerHTML = html;
        
    } catch (error) {
        showError(statusDiv, error.message);
    }
}

// ==================== CHAT ====================

/**
 * Send a chat message
 */
async function sendChat() {
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const latencyDiv = document.getElementById('chatLatency');
    const ragSourcesDiv = document.getElementById('ragSources');
    
    const question = chatInput.value.trim();
    
    if (!currentProjectId) {
        const errorMsg = 'Please select a project first';
        showError(latencyDiv, errorMsg);
        alert(errorMsg);
        return;
    }
    
    if (!question) {
        const errorMsg = 'Please enter a question';
        showError(latencyDiv, errorMsg);
        alert(errorMsg);
        return;
    }
    
    console.log(`Sending chat - Project ID: ${currentProjectId}, Question: ${question}`);
    
    // Clear previous messages on first message
    if (chatMessages.querySelector('.text-gray-400')) {
        chatMessages.innerHTML = '';
    }
    
    // Add user message
    addChatMessage('user', question);
    chatInput.value = '';
    
    try {
        const startTime = Date.now();
        
        // Show loading
        const loadingId = addChatMessage('assistant', 'Thinking...');
        
        const response = await fetch(`${API_BASE}/chat/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                message: question  // API expects 'message', not 'question'
            })
        });
        
        console.log('Chat response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Chat error response:', errorText);
            let errorDetail = 'Chat request failed';
            try {
                const errorJson = JSON.parse(errorText);
                errorDetail = errorJson.detail || errorDetail;
            } catch (e) {
                errorDetail = errorText || errorDetail;
            }
            throw new Error(errorDetail);
        }
        
        const data = await response.json();
        const latency = Date.now() - startTime;
        
        // Remove loading message
        document.getElementById(loadingId).remove();
        
        // Add bot response
        addChatMessage('assistant', data.answer);
        
        // Show latency
        latencyDiv.textContent = `Response time: ${latency}ms`;
        
        // Display RAG sources
        displayRagSources(data.sources);
        
    } catch (error) {
        console.error('Chat error:', error);
        const errorMsg = error.message || String(error) || 'Chat request failed';
        showError(latencyDiv, errorMsg);
        
        // Remove loading message if it exists
        const loadingMsg = chatMessages.querySelector('.loading');
        if (loadingMsg) loadingMsg.remove();
    }
}

/**
 * Add a message to chat window
 */
function addChatMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageId = `msg-${Date.now()}-${Math.random()}`;
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `mb-3 ${role === 'user' ? 'text-right' : 'text-left'}`;
    
    const bubble = document.createElement('div');
    bubble.className = `inline-block max-w-[80%] p-3 rounded-lg ${
        role === 'user' 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-200 text-gray-800'
    }`;
    bubble.textContent = content;
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

/**
 * Display RAG sources
 */
function displayRagSources(sources) {
    const ragSourcesDiv = document.getElementById('ragSources');
    
    if (!sources || sources.length === 0) {
        ragSourcesDiv.innerHTML = '<p class="text-gray-400">No sources returned</p>';
        return;
    }
    
    let html = '<div class="space-y-2">';
    
    sources.forEach((source, index) => {
        const preview = source.text.substring(0, 200) + (source.text.length > 200 ? '...' : '');
        html += `
            <div class="bg-gray-50 p-3 rounded border border-gray-200">
                <div class="flex justify-between items-start mb-1">
                    <span class="font-semibold text-gray-700">Chunk ${index + 1}</span>
                    <span class="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Score: ${source.score.toFixed(3)}</span>
                </div>
                <div class="text-xs text-gray-500 mb-1">Chunk ID: ${source.chunk_id}</div>
                <div class="text-sm text-gray-700">${preview}</div>
            </div>
        `;
    });
    
    html += '</div>';
    ragSourcesDiv.innerHTML = html;
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Check server connection on startup
 */
async function checkServerConnection() {
    try {
        const baseUrl = window.location.hostname ? '' : 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Server connected:', data.message);
            console.log('✅ API Base URL:', API_BASE);
        }
    } catch (error) {
        console.error('❌ Server connection failed:', error);
        const resultDiv = document.getElementById('projectCreateResult');
        const errorMsg = error.message || String(error) || 'Connection failed';
        const accessMethod = window.location.protocol === 'file:' 
            ? 'You are opening the file directly. Use http://localhost:8000/ui/index.html instead'
            : `Cannot connect to server at ${window.location.origin}`;
        showError(resultDiv, `${accessMethod}. Error: ${errorMsg}`);
    }
}

function showSuccess(element, message) {
    element.innerHTML = `<p class="text-green-600 font-semibold">✓ ${message}</p>`;
}

function showError(element, message) {
    element.innerHTML = `<p class="text-red-600 font-semibold">✗ ${message}</p>`;
}

function showInfo(element, message) {
    element.innerHTML = `<p class="text-blue-600">${message}</p>`;
}

// Handle Enter key in chat input
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChat();
            }
        });
    }
});
