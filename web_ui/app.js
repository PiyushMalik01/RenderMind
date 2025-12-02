// WebSocket connection
let ws = null;
let reconnectInterval = null;
const WS_URL = 'ws://localhost:8765';

// Voice recording
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// DOM elements
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const charCount = document.getElementById('char-count');
const statusIndicator = document.querySelector('.status-indicator');
const statusText = document.getElementById('status-text');
const voiceBtn = document.getElementById('voice-btn');
const voiceIcon = document.getElementById('voice-icon');

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    setupEventListeners();
    adjustTextareaHeight();
    checkMicrophoneSupport();
});

// WebSocket connection
function connectWebSocket() {
    try {
        console.log('Attempting to connect to', WS_URL);
        ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
            console.log('Connected to RenderMind');
            updateConnectionStatus(true);
            stopReconnecting();
            
            // Send ping to keep alive
            setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    sendToServer({ type: 'ping' });
                }
            }, 30000);
            
            // Load existing messages
            loadMessages();
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = (event) => {
            console.log('Disconnected from RenderMind', {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
            updateConnectionStatus(false);
            startReconnecting();
        };
    } catch (error) {
        console.error('Failed to connect:', error);
        updateConnectionStatus(false);
        startReconnecting();
    }
}

function startReconnecting() {
    if (!reconnectInterval) {
        console.log('Will retry connection in 3 seconds...');
        reconnectInterval = setInterval(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
        }, 3000);
    }
}

function stopReconnecting() {
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
    }
}

function updateConnectionStatus(connected) {
    if (connected) {
        statusIndicator.classList.add('connected');
        statusIndicator.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.classList.add('disconnected');
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

// Event listeners
function setupEventListeners() {
    // Send button
    sendBtn.addEventListener('click', sendMessage);
    
    // Enter to send (Shift+Enter for newline)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Character counter
    userInput.addEventListener('input', () => {
        const length = userInput.value.length;
        charCount.textContent = `${length}/4096`;
        adjustTextareaHeight();
        
        if (length > 4096) {
            charCount.style.color = '#f48771';
        } else {
            charCount.style.color = '#808080';
        }
    });
    
    // Quick action buttons
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            handleQuickAction(action);
        });
    });
}

// Send message to server
function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message) {
        console.log('Cannot send: message empty');
        return;
    }
    
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.log('Cannot send: WebSocket not connected', {
            wsExists: !!ws,
            wsState: ws ? ws.readyState : 'no ws',
            wsOpen: WebSocket.OPEN
        });
        alert('Not connected to Blender. Please check if the Web Server is running in Blender.');
        return;
    }
    
    console.log('Sending message:', message);
    
    // Clear input
    userInput.value = '';
    charCount.textContent = '0/4096';
    adjustTextareaHeight();
    
    // Send to server
    sendToServer({
        type: 'send_message',
        message: message
    });
    
    // Add to UI
    addMessage({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
    });
    
    // Show thinking indicator
    showThinking();
}

// Quick actions
function quickAction(text) {
    userInput.value = text;
    userInput.focus();
    userInput.setSelectionRange(text.length, text.length);
    adjustTextareaHeight();
    
    // Update character count
    const length = text.length;
    charCount.textContent = `${length}/4096`;
}

function handleQuickAction(action) {
    let message = '';
    
    switch (action) {
        case 'create':
            message = 'Create a new object';
            break;
        case 'modify':
            message = 'Modify the selected object';
            break;
        case 'material':
            message = 'Apply materials to the selected object';
            break;
        case 'clear':
            clearChat();
            return;
    }
    
    quickAction(message);
}

// Clear chat
function clearChat() {
    if (!confirm('Are you sure you want to clear all messages?')) {
        return;
    }
    
    sendToServer({ type: 'clear_chat' });
    chatMessages.innerHTML = '';
    addWelcomeMessage();
}

// Load messages from server
function loadMessages() {
    sendToServer({ type: 'get_messages' });
}

// Send message via WebSocket
function sendToServer(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// Handle messages from server
function handleServerMessage(data) {
    console.log('Received message:', data);
    
    switch (data.type) {
        case 'pong':
            // Keep-alive response
            break;
            
        case 'messages':
        case 'messages_list':
            // Load existing messages
            chatMessages.innerHTML = '';
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => addMessage(msg));
            } else {
                addWelcomeMessage();
            }
            break;
            
        case 'new_message':
        case 'message_response':
            // New message from assistant
            hideThinking();
            if (data.message) {
                addMessage(data.message);
            }
            break;
        
        case 'transcription':
            // Handle voice transcription
            if (data.text) {
                handleTranscription(data.text);
            } else if (data.error) {
                alert('Transcription failed: ' + data.error);
                voiceBtn.disabled = false;
                voiceIcon.textContent = '🎤';
            }
            break;
            
        case 'error':
            hideThinking();
            showError(data.message);
            break;
            
        case 'chat_cleared':
            chatMessages.innerHTML = '';
            addWelcomeMessage();
            break;
    }
}

// Add message to UI
function addMessage(message) {
    const messageDiv = document.createElement('div');
    
    // Handle different role formats (USER/AI or user/assistant)
    const role = (message.role || '').toLowerCase();
    const isUser = role === 'user' || role === 'USER';
    const isAssistant = role === 'assistant' || role === 'ai' || role === 'AI';
    
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}-message`;
    
    const avatar = isUser ? '👤' : '🤖';
    const name = isUser ? 'You' : 'RenderMind';
    
    const timestamp = message.timestamp ? 
        new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 
        '';
    
    let contentHTML = `
        <div class="message-header">
            <span class="avatar">${avatar}</span>
            <span class="name">${name}</span>
            <span class="timestamp">${timestamp}</span>
        </div>
        <div class="message-content">
            <p>${escapeHtml(message.content)}</p>
    `;
    
    // Add code block if present
    if (message.code) {
        const status = (message.status || '').toLowerCase();
        const statusBadge = status && status !== 'none' ? `
            <div class="status-badge ${status === 'success' ? 'success' : 'error'}">
                ${status === 'success' ? '✓ Executed' : status === 'error' ? '✗ Error' : status}
            </div>
        ` : '';
        
        contentHTML += `
            <div class="code-block">
                <div class="code-header">
                    <span>Python</span>
                    <div class="code-actions">
                        <button class="code-btn copy-btn" onclick="copyCode(this)">📋 Copy</button>
                        <button class="code-btn run-btn" onclick="runCode('${escapeQuotes(message.code)}')">▶️ Run</button>
                    </div>
                </div>
                <div class="code-content">
                    <pre>${escapeHtml(message.code)}</pre>
                </div>
            </div>
            ${statusBadge}
        `;
    }
    
    // Add error message if present
    if (message.error_msg) {
        contentHTML += `
            <div class="status-badge error">
                ✗ ${escapeHtml(message.error_msg)}
            </div>
        `;
    }
    
    contentHTML += '</div>';
    messageDiv.innerHTML = contentHTML;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Welcome message
function addWelcomeMessage() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'message system-message';
    welcomeDiv.innerHTML = `
        <div class="message-header">
            <span class="avatar">🚀</span>
            <span class="name">RenderMind</span>
        </div>
        <div class="message-content">
            <p>Welcome to RenderMind! I'm your AI assistant for Blender.</p>
            <p class="hint">Ask me to create, modify, or enhance your 3D projects.</p>
        </div>
    `;
    chatMessages.appendChild(welcomeDiv);
}

// Show thinking indicator
function showThinking() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.className = 'message assistant-message';
    thinkingDiv.innerHTML = `
        <div class="message-header">
            <span class="avatar">🤖</span>
            <span class="name">RenderMind</span>
        </div>
        <div class="message-content">
            <div class="thinking">
                <span>Thinking</span>
                <div class="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(thinkingDiv);
    scrollToBottom();
}

function hideThinking() {
    const thinking = document.getElementById('thinking-indicator');
    if (thinking) {
        thinking.remove();
    }
}

// Show error message
function showError(errorMsg) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message system-message';
    errorDiv.innerHTML = `
        <div class="message-header">
            <span class="avatar">⚠️</span>
            <span class="name">System</span>
        </div>
        <div class="message-content">
            <div class="status-badge error">
                ✗ ${escapeHtml(errorMsg)}
            </div>
        </div>
    `;
    chatMessages.appendChild(errorDiv);
    scrollToBottom();
}

// Copy code to clipboard
function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    const code = codeBlock.querySelector('pre').textContent;
    
    navigator.clipboard.writeText(code).then(() => {
        const originalText = button.textContent;
        button.textContent = '✓ Copied!';
        button.style.color = '#4ec9b0';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Run code in Blender
function runCode(code) {
    sendToServer({
        type: 'execute_code',
        code: code
    });
}

// Utility functions
function adjustTextareaHeight() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 200) + 'px';
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeQuotes(text) {
    return text.replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

// Voice Input Functions
function checkMicrophoneSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        voiceBtn.disabled = true;
        voiceBtn.title = 'Microphone not supported';
        console.warn('Microphone not supported in this browser');
    }
}

async function toggleVoiceInput() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await transcribeAudio(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        voiceBtn.classList.add('recording');
        voiceIcon.textContent = '⏹️';
        console.log('Recording started');
        
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not access microphone. Please check permissions.');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        voiceBtn.classList.remove('recording');
        voiceIcon.textContent = '🎤';
        console.log('Recording stopped');
    }
}

async function transcribeAudio(audioBlob) {
    try {
        // Show loading state
        voiceBtn.disabled = true;
        voiceIcon.textContent = '⏳';
        
        // Send audio to server for transcription
        sendToServer({
            type: 'transcribe_audio',
            audio: await blobToBase64(audioBlob)
        });
        
    } catch (error) {
        console.error('Transcription error:', error);
        alert('Failed to transcribe audio');
        voiceBtn.disabled = false;
        voiceIcon.textContent = '🎤';
    }
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

function handleTranscription(text) {
    // Insert transcribed text into input
    userInput.value = text;
    userInput.focus();
    
    // Update character count
    const length = text.length;
    charCount.textContent = `${length}/4096`;
    
    // Reset voice button
    voiceBtn.disabled = false;
    voiceIcon.textContent = '🎤';
    
    adjustTextareaHeight();
}
