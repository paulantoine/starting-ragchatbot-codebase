// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let currentAbortController = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');

    setupEventListeners();
    initializeTheme();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New chat button
    newChatButton.addEventListener('click', startNewChat);

    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);
    themeToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTheme();
        }
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Cancel any ongoing request
    if (currentAbortController) {
        currentAbortController.abort();
    }

    // Create new abort controller for this request
    currentAbortController = new AbortController();

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            }),
            signal: currentAbortController.signal
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error (unless aborted)
        if (error.name !== 'AbortError') {
            loadingMessage.remove();
            addMessage(`Error: ${error.message}`, 'assistant');
        } else {
            // Remove loading message if request was aborted
            loadingMessage.remove();
        }
    } finally {
        // Clear the abort controller
        currentAbortController = null;
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        // Handle both old string format and new structured format
        const sourceElements = sources.map((source, index) => {
            let sourceContent = '';
            if (typeof source === 'string') {
                // Legacy string format
                sourceContent = `<span class="source-text">${source}</span>`;
            } else if (source && typeof source === 'object') {
                // New structured format with optional links
                if (source.link) {
                    sourceContent = `<a href="${source.link}" target="_blank" class="source-text clickable-source">${source.text}</a>`;
                } else {
                    sourceContent = `<span class="source-text">${source.text}</span>`;
                }
            } else {
                sourceContent = `<span class="source-text">${source}</span>`;
            }

            return `
                <div class="source-item">
                    <div class="source-number">${index + 1}</div>
                    ${sourceContent}
                </div>
            `;
        });

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources (${sources.length})</summary>
                <div class="sources-content">
                    ${sourceElements.join('')}
                </div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

async function startNewChat() {
    try {
        // Cancel any ongoing request
        if (currentAbortController) {
            currentAbortController.abort();
            currentAbortController = null;
        }

        // Clear session on backend if we have a session ID
        if (currentSessionId) {
            try {
                await fetch(`${API_URL}/sessions/clear`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: currentSessionId
                    })
                });
            } catch (error) {
                console.warn('Failed to clear session on backend:', error);
                // Continue with frontend cleanup even if backend fails
            }
        }

        // Reset frontend state
        currentSessionId = null;
        chatMessages.innerHTML = '';

        // Clear any input
        chatInput.value = '';
        chatInput.disabled = false;
        sendButton.disabled = false;

        // Add welcome message
        addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);

        // Focus on input
        chatInput.focus();

    } catch (error) {
        console.error('Error starting new chat:', error);
        // Still try to reset frontend state
        currentSessionId = null;
        chatMessages.innerHTML = '';
        chatInput.value = '';
        chatInput.disabled = false;
        sendButton.disabled = false;
        addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
        chatInput.focus();
    }
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}

// Theme Functions
function initializeTheme() {
    // Check if user has a saved theme preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Default to dark theme if no saved preference, or use saved preference
    const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light');
    
    // Apply theme
    if (initialTheme === 'light') {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
    }
    
    // Update button aria-label
    updateThemeToggleLabel();
}

function toggleTheme() {
    const isLightTheme = document.body.classList.contains('light-theme');
    
    if (isLightTheme) {
        // Switch to dark theme
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    } else {
        // Switch to light theme
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
    }
    
    // Update button aria-label
    updateThemeToggleLabel();
}

function updateThemeToggleLabel() {
    const isLightTheme = document.body.classList.contains('light-theme');
    const label = isLightTheme ? 'Switch to dark theme' : 'Switch to light theme';
    themeToggle.setAttribute('aria-label', label);
}