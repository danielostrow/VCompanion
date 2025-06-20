class ChatInterface {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.chatMessages = document.getElementById('chatMessages');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.currentCharacterName = 'Sally';
        this.currentAvatar = '/static/default-avatar.png';
        this.isAwaitingResponse = false;
        this.userAvatar = '/static/user-avatar.png';
        
        this.initializeEventListeners();
        this.loadInitialAvatar();
    }

    initializeEventListeners() {
        // Send message on Enter key
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize input and enable/disable send button
        this.messageInput.addEventListener('input', () => {
            this.updateSendButtonState();
        });

        // Close modals when clicking outside
        document.addEventListener('click', (e) => {
            const changeModal = document.getElementById('changeModal');
            const helpModal = document.getElementById('helpModal');
            
            if (e.target === changeModal) {
                this.closeChangeModal();
            }
            if (e.target === helpModal) {
                this.closeHelpModal();
            }
        });

        this.updateSendButtonState();
    }

    updateSendButtonState() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isAwaitingResponse;
    }

    async loadInitialAvatar() {
        try {
            await this.generateProfilePhoto('Sally', 'Sally - 23, barista at Starbucks, just finished a lit degree, loves concerts and friends');
        } catch (error) {
            console.log('Using default avatar');
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isAwaitingResponse) return;

        // Check if it's a /change command
        if (message.toLowerCase().startsWith('/change')) {
            this.handleChangeCommand(message);
            return;
        }

        this.addUserMessage(message);
        this.messageInput.value = '';
        this.updateSendButtonState();
        
        await this.sendToAPI(message);
    }

    handleChangeCommand(message) {
        const changeText = message.substring(7).trim();
        if (!changeText) {
            this.addSystemMessage("Use: /change [description]\nExample: /change you're now Emma, a 25-year-old artist from Brooklyn");
            return;
        }
        
        // Show change modal with pre-filled text
        document.getElementById('changeInput').value = changeText;
        this.showChangeModal();
    }

    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <img src="${this.userAvatar}" alt="You" class="message-avatar">
                <div>
                    <div class="message-bubble">${this.escapeHtml(text)}</div>
                    <div class="message-time">${this.formatTime(new Date())}</div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addAssistantMessage(text, activity = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        
        let activityBadge = '';
        if (activity && activity.activity) {
            activityBadge = `<div class="activity-badge">${activity.activity}</div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <img src="${this.currentAvatar}" alt="${this.currentCharacterName}" class="message-avatar">
                <div>
                    <div class="message-bubble">${this.escapeHtml(text)}</div>
                    ${activityBadge}
                    <div class="message-time">${this.formatTime(new Date())}</div>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.style.textAlign = 'center';
        messageDiv.style.margin = '20px 0';
        messageDiv.style.color = '#65676b';
        messageDiv.style.fontSize = '13px';
        
        messageDiv.innerHTML = `<div style="background: #f0f2f5; padding: 10px; border-radius: 12px; display: inline-block;">${this.escapeHtml(text)}</div>`;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        // Update typing indicator avatar
        document.getElementById('typingAvatar').src = this.currentAvatar;
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    async sendToAPI(message) {
        this.isAwaitingResponse = true;
        this.updateSendButtonState();
        this.showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            this.hideTypingIndicator();
            this.addAssistantMessage(data.reply, data.activity);

            // Update character status if available
            if (data.activity) {
                this.updateCharacterStatus(data.activity);
            }

            // Check if character transformation is complete and update avatar
            if (data.new_avatar) {
                // Extract character name from transformation message
                const nameMatch = data.reply.match(/I'm (\w+)/i) || data.reply.match(/(\w+) here/i);
                const newName = nameMatch ? nameMatch[1] : 'Character';
                this.updateCharacterAvatar(data.new_avatar, newName);
                this.addSystemMessage("🎭 New character photo generated!");
            } else if (data.reply.includes('follow-up questions') || data.reply.includes('questions')) {
                // Character change is in progress
                this.addSystemMessage("Answer the questions above to complete the transformation!");
            }

        } catch (error) {
            this.hideTypingIndicator();
            this.addSystemMessage(`Error: ${error.message}`);
        } finally {
            this.isAwaitingResponse = false;
            this.updateSendButtonState();
        }
    }

    async submitChange() {
        const changeText = document.getElementById('changeInput').value.trim();
        if (!changeText) return;

        this.closeChangeModal();
        
        // Add user message
        this.addUserMessage(`/change ${changeText}`);
        
        this.isAwaitingResponse = true;
        this.updateSendButtonState();
        this.showTypingIndicator();

        try {
            // Send change command
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: `/change ${changeText}` })
            });

            const data = await response.json();
            this.hideTypingIndicator();
            this.addAssistantMessage(data.reply, data.activity);

            // If this is the follow-up questions stage, wait for user response
            if (data.reply.includes('follow-up questions') || data.reply.includes('questions')) {
                // Character change is in progress
                this.addSystemMessage("Answer the questions above to complete the transformation!");
            }

        } catch (error) {
            this.hideTypingIndicator();
            this.addSystemMessage(`Error: ${error.message}`);
        } finally {
            this.isAwaitingResponse = false;
            this.updateSendButtonState();
        }
    }

    async generateProfilePhoto(characterName = null, characterDesc = null) {
        try {
            const name = characterName || this.currentCharacterName;
            const desc = characterDesc || `${this.currentCharacterName} - AI companion`;
            
            const response = await fetch('/generate_photo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    character_name: name,
                    character_description: desc 
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.avatar_url) {
                    this.updateCharacterAvatar(data.avatar_url, name);
                }
            }
        } catch (error) {
            console.error('Error generating photo:', error);
        }
    }

    updateCharacterAvatar(avatarUrl, characterName = null) {
        this.currentAvatar = avatarUrl;
        if (characterName) {
            this.currentCharacterName = characterName;
        }

        // Update all avatar images
        document.getElementById('characterAvatar').src = avatarUrl;
        document.getElementById('welcomeAvatar').src = avatarUrl;
        document.getElementById('typingAvatar').src = avatarUrl;
        
        // Update character name
        document.getElementById('characterName').textContent = this.currentCharacterName;
        document.getElementById('welcomeName').textContent = this.currentCharacterName;
    }

    updateCharacterStatus(activity) {
        const statusElement = document.getElementById('characterStatus');
        if (activity && activity.activity) {
            statusElement.textContent = activity.activity;
        } else {
            statusElement.textContent = 'Active now';
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Modal functions
    showChangeModal() {
        document.getElementById('changeModal').style.display = 'flex';
    }

    closeChangeModal() {
        document.getElementById('changeModal').style.display = 'none';
        document.getElementById('changeInput').value = '';
    }

    showHelpModal() {
        document.getElementById('helpModal').style.display = 'flex';
    }

    closeHelpModal() {
        document.getElementById('helpModal').style.display = 'none';
    }

    async resetMemory() {
        if (!confirm('Are you sure you want to reset the memory? This will clear all conversation history.')) {
            return;
        }

        try {
            const response = await fetch('/reset', {
                method: 'POST'
            });

            if (response.ok) {
                // Clear chat messages except welcome
                const messages = this.chatMessages.querySelectorAll('.message');
                messages.forEach(msg => msg.remove());
                
                this.addSystemMessage('Memory reset! Starting fresh conversation.');
            }
        } catch (error) {
            this.addSystemMessage(`Error resetting memory: ${error.message}`);
        }
    }
}

// Initialize chat interface when page loads
let chatInterface;

document.addEventListener('DOMContentLoaded', () => {
    chatInterface = new ChatInterface();
});

// Global functions for HTML onclick events
function sendMessage() {
    chatInterface.sendMessage();
}

function showChangeModal() {
    chatInterface.showChangeModal();
}

function closeChangeModal() {
    chatInterface.closeChangeModal();
}

function submitChange() {
    chatInterface.submitChange();
}

function showHelpModal() {
    chatInterface.showHelpModal();
}

function closeHelpModal() {
    chatInterface.closeHelpModal();
}

function resetMemory() {
    chatInterface.resetMemory();
}

function generateNewPhoto() {
    chatInterface.generateProfilePhoto();
} 