// ===================================
// Configuration
// ===================================
let config = {
    apiUrl: 'http://127.0.0.1:8765',
    sessionId: 'default',
    maxRetries: 3
};

// Load config from localStorage
function loadConfig() {
    const saved = localStorage.getItem('filesearch-config');
    if (saved) {
        config = { ...config, ...JSON.parse(saved) };
    }
    updateConfigUI();
}

function saveConfig() {
    localStorage.setItem('filesearch-config', JSON.stringify(config));
}

function updateConfigUI() {
    // Removed UI updates since we simplified the interface
}

// ===================================
// Backend Connection
// ===================================
let backendStatus = {
    isOnline: false,
    lastCheck: null,
    version: null,
    indexedDocs: 0
};

async function checkBackendHealth() {
    try {
        const response = await fetch(`${config.apiUrl}/health`);
        const data = await response.json();
        
        backendStatus = {
            isOnline: response.ok,
            lastCheck: new Date(),
            version: data.version,
            indexedDocs: data.indexed_documents
        };
        
        updateStatusUI();
        return true;
    } catch (error) {
        console.error('Backend health check failed:', error);
        backendStatus.isOnline = false;
        backendStatus.lastCheck = new Date();
        updateStatusUI();
        return false;
    }
}

function updateStatusUI() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const sendBtn = document.getElementById('sendBtn');
    
    if (backendStatus.isOnline) {
        statusDot.className = 'status-dot online';
        statusText.textContent = 'Active';
        sendBtn.disabled = false;
    } else {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Activating...';
        sendBtn.disabled = true;
    }
}

// Check backend every 10 seconds
setInterval(checkBackendHealth, 10000);

// ===================================
// Message Handling
// ===================================
function addMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    
    // Remove welcome message on first real message
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = content;
    
    const timestamp = document.createElement('small');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = new Date().toLocaleTimeString();
    
    contentDiv.appendChild(textDiv);
    contentDiv.appendChild(timestamp);
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

function showTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'flex';
    
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || !backendStatus.isOnline) return;
    
    // Add user message
    addMessage('user', message);
    input.value = '';
    input.style.height = 'auto';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${config.apiUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: config.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide typing and add assistant response
        hideTypingIndicator();
        addMessage('assistant', data.response);
        
        // Refresh documents list if needed
        if (message.toLowerCase().includes('index')) {
            setTimeout(refreshDocuments, 1000);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessage('assistant', `❌ Error: ${error.message}\n\nMake sure the backend server is running: python api_server.py`);
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Auto-resize textarea
document.getElementById('messageInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

// ===================================
// Document Management
// ===================================
async function refreshDocuments() {
    try {
        const response = await fetch(`${config.apiUrl}/api/indexed-documents`);
        const data = await response.json();
        
        const docsList = document.getElementById('documentsList');
        
        if (data.count === 0) {
            docsList.innerHTML = '<p class="empty-state">No documents indexed yet</p>';
        } else {
            docsList.innerHTML = '';
            data.documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'document-item';
                item.innerHTML = `
                    <i class="fas fa-file-alt"></i>
                    <div>
                        <strong>${doc.filename}</strong>
                        <br>
                        <small>${doc.chunk_count} chunks</small>
                    </div>
                `;
                item.onclick = () => {
                    document.getElementById('messageInput').value = `Query ${doc.filename}: `;
                    document.getElementById('messageInput').focus();
                };
                docsList.appendChild(item);
            });
        }
        
        // Update status
        backendStatus.indexedDocs = data.count;
        updateStatusUI();
        
    } catch (error) {
        console.error('Error fetching documents:', error);
    }
}

// ===================================
// Session Management
// ===================================
function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <i class="fas fa-robot"></i>
                <h2>Chat Cleared! 🗑️</h2>
                <p>Start a new conversation by asking me anything.</p>
            </div>
        `;
    }
}

async function newSession() {
    const newSessionId = prompt('Enter a name for the new session:', `session-${Date.now()}`);
    
    if (newSessionId) {
        config.sessionId = newSessionId;
        saveConfig();
        updateConfigUI();
        clearChat();
        
        addMessage('assistant', `✅ Started new session: ${newSessionId}\n\nAll previous context has been cleared. How can I help you?`);
    }
}

// ===================================
// Modal Controls
// ===================================
function toggleHelp() {
    const modal = document.getElementById('helpModal');
    modal.classList.toggle('active');
}

// Close modals on outside click
window.onclick = function(event) {
    const helpModal = document.getElementById('helpModal');
    
    if (event.target === helpModal) {
        helpModal.classList.remove('active');
    }
}

// ===================================
// Example Questions
// ===================================
function useExample(element) {
    const text = element.querySelector('span').textContent;
    document.getElementById('messageInput').value = text;
    document.getElementById('messageInput').focus();
    toggleHelp();
}

// ===================================
// Initialization
// ===================================
async function initialize() {
    console.log('🚀 Initializing Local Agent UI...');
    
    // Load config
    loadConfig();
    
    // Check backend
    const isOnline = await checkBackendHealth();
    
    if (isOnline) {
        console.log('✅ Backend is online!');
        refreshDocuments();
        
        addMessage('assistant', 
            `👋 Hello! I'm your AI file search assistant.\n\n` +
            `I can help you find files, index documents, and answer questions about your data.\n\n` +
            `What would you like me to do?`
        );
    } else {
        console.error('❌ Backend is offline!');
        
        addMessage('assistant', 
            `🤖 Agent is activating, please wait...\n\n` +
            `The AI assistant is starting up. This may take a few moments.\n\n` +
            `Feel free to type your question, and I'll respond once ready! ⏳`
        );
    }
    
    // Focus input
    document.getElementById('messageInput').focus();
}

// Start when page loads
window.addEventListener('DOMContentLoaded', initialize);

// ===================================
// Keyboard Shortcuts
// ===================================
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + K - Focus input
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        document.getElementById('messageInput').focus();
    }
    
    // Ctrl/Cmd + L - Clear chat
    if ((event.ctrlKey || event.metaKey) && event.key === 'l') {
        event.preventDefault();
        clearChat();
    }
    
    // Escape - Close modals
    if (event.key === 'Escape') {
        document.getElementById('helpModal').classList.remove('active');
        document.getElementById('settingsModal').classList.remove('active');
    }
});

// ===================================
// Service Worker (optional - for offline support)
// ===================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment to enable service worker
        // navigator.serviceWorker.register('/sw.js')
        //     .then(reg => console.log('Service Worker registered'))
        //     .catch(err => console.log('Service Worker registration failed'));
    });
}
