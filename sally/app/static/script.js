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
            console.log('Loading character state...');
            
            // Get current character state from server
            const response = await fetch('/character');
            
            if (response.ok) {
                const character = await response.json();
                console.log('Loaded character:', character);
                
                // Update character info and UI
                this.currentCharacterName = character.name;
                this.updateCharacterAvatar(character.avatar_path, character.name);
                
                console.log(`Character ${character.name} loaded successfully`);
            } else {
                console.log('Failed to load character state, using defaults');
                this.updateCharacterAvatar('/static/default-avatar.png', 'Sally');
            }
        } catch (error) {
            console.log('Error loading character state, using defaults:', error);
            this.updateCharacterAvatar('/static/default-avatar.png', 'Sally');
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isAwaitingResponse) return;

        // Check if it's a /change command
        if (message.toLowerCase().startsWith('/change')) {
            const changeText = message.substring(7).trim();
            if (!changeText) {
                this.addSystemMessage("Use: /change [description]\nExample: /change you're now Emma, a 25-year-old artist from Brooklyn");
                return;
            }
            
            // Clear input and show transformation modal
            this.messageInput.value = '';
            this.updateSendButtonState();
            this.showTransformationModal(changeText);
            
            this.isAwaitingResponse = true;
            this.updateSendButtonState();

            try {
                // Send change command - no timeout, let avatar generation take as long as needed
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: `/change ${changeText}` })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                // Log the actual response for debugging
                console.log('🔍 Server response:', data);

                // Check if character transformation is complete
                if (data.character_name && data.new_avatar) {
                    // Store avatar info if present
                    if (data.avatar_info) {
                        this.lastAvatarInfo = data.avatar_info;
                    }
                    
                    // Complete the transformation flow
                    await this.completeTransformation(data.character_name, data.new_avatar, data.reply);
                } else if (data.character_name || data.new_avatar) {
                    // Partial success - handle gracefully
                    console.log('⚠️ Partial transformation data received:', data);
                    this.hideTransformationModal();
                    this.addSystemMessage("Transformation partially completed. Please refresh the page to see changes.");
                } else {
                    // Handle error case - but check if transformation actually succeeded
                    console.log('❌ Transformation failed - missing required fields:', data);
                    
                    // Wait a moment then check current character state as fallback
                    setTimeout(async () => {
                        try {
                            const statusResponse = await fetch('/character');
                            if (statusResponse.ok) {
                                const currentChar = await statusResponse.json();
                                console.log('🔍 Checking character state after failed response:', currentChar);
                                
                                // Check if character actually changed (different from original)
                                if (currentChar.name !== 'Sally' || currentChar.avatar_path !== '/static/default-avatar.png') {
                                    console.log('✅ Transformation actually succeeded - updating UI');
                                    this.hideTransformationModal();
                                    this.updateCharacterAvatar(currentChar.avatar_path, currentChar.name);
                                    this.addSystemMessage(`🎭 Transformation succeeded! You're now chatting with ${currentChar.name}.`);
                                    return; // Success detected
                                }
                            }
                        } catch (statusError) {
                            console.log('❌ Could not verify character state:', statusError);
                        }
                        
                        // If we get here, transformation truly failed
                        this.hideTransformationModal();
                        this.addSystemMessage("Transformation failed. Please try again.");
                    }, 2000); // Wait 2 seconds before checking
                }

            } catch (error) {
                console.log('💥 Error during transformation:', error);
                this.hideTransformationModal();
                this.addSystemMessage(`Error: ${error.message}`);
            } finally {
                this.isAwaitingResponse = false;
                this.updateSendButtonState();
            }
            return;
        }

        // Regular message handling
        this.addUserMessage(message);
        this.messageInput.value = '';
        this.updateSendButtonState();
        
        await this.sendToAPI(message);
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

    addAssistantMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <img src="${this.currentAvatar}" alt="${this.currentCharacterName}" class="message-avatar">
                <div>
                    <div class="message-bubble">${this.escapeHtml(text)}</div>
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
            this.addAssistantMessage(data.reply);

            // Check if character transformation is complete and update avatar/name immediately
            if (data.character_name && data.new_avatar) {
                this.updateCharacterAvatar(data.new_avatar, data.character_name);
                this.addSystemMessage(`🎭 Transformed into ${data.character_name}!`);
                
                // Force page refresh after transformation to ensure clean state
                setTimeout(() => {
                    console.log(`🔄 Refreshing page for clean ${data.character_name} state...`);
                    window.location.reload();
                }, 1500); // Short delay to show the transformation message
                
            } else if (data.new_avatar) {
                // Just avatar update
                this.updateCharacterAvatar(data.new_avatar);
                this.addSystemMessage("🎭 New character photo generated!");
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
        
        // Show transformation modal instead of adding user message immediately
        this.showTransformationModal(changeText);
        
        this.isAwaitingResponse = true;
        this.updateSendButtonState();

        try {
            // Send change command - no timeout, let avatar generation take as long as needed
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: `/change ${changeText}` })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Log the actual response for debugging
            console.log('🔍 Server response:', data);

            // Check if character transformation is complete
            if (data.character_name && data.new_avatar) {
                // Store avatar info if present
                if (data.avatar_info) {
                    this.lastAvatarInfo = data.avatar_info;
                }
                
                // Complete the transformation flow
                await this.completeTransformation(data.character_name, data.new_avatar, data.reply);
            } else if (data.character_name || data.new_avatar) {
                // Partial success - handle gracefully
                console.log('⚠️ Partial transformation data received:', data);
                this.hideTransformationModal();
                this.addSystemMessage("Transformation partially completed. Please refresh the page to see changes.");
            } else {
                // Handle error case - but check if transformation actually succeeded
                console.log('❌ Transformation failed - missing required fields:', data);
                
                // Wait a moment then check current character state as fallback
                setTimeout(async () => {
                    try {
                        const statusResponse = await fetch('/character');
                        if (statusResponse.ok) {
                            const currentChar = await statusResponse.json();
                            console.log('🔍 Checking character state after failed response:', currentChar);
                            
                            // Check if character actually changed (different from original)
                            if (currentChar.name !== 'Sally' || currentChar.avatar_path !== '/static/default-avatar.png') {
                                console.log('✅ Transformation actually succeeded - updating UI');
                                this.hideTransformationModal();
                                this.updateCharacterAvatar(currentChar.avatar_path, currentChar.name);
                                this.addSystemMessage(`🎭 Transformation succeeded! You're now chatting with ${currentChar.name}.`);
                                return; // Success detected
                            }
                        }
                    } catch (statusError) {
                        console.log('❌ Could not verify character state:', statusError);
                    }
                    
                    // If we get here, transformation truly failed
                    this.hideTransformationModal();
                    this.addSystemMessage("Transformation failed. Please try again.");
                }, 2000); // Wait 2 seconds before checking
            }

        } catch (error) {
            console.log('💥 Error during transformation:', error);
            this.hideTransformationModal();
            this.addSystemMessage(`Error: ${error.message}`);
        } finally {
            this.isAwaitingResponse = false;
            this.updateSendButtonState();
        }
    }

    showTransformationModal(changeText) {
        console.log('🎭 Starting transformation modal...');
        
        // Store the change text for later use
        this.currentChangeText = changeText;
        
        // Set up current character info - show actual current character name
        document.getElementById('oldCharacterImg').src = this.currentAvatar;
        document.getElementById('currentCharacterLabel').textContent = this.currentCharacterName;
        
        // Extract new character name from change description and set it
        const expectedNewName = this.extractCharacterNameFromChange(changeText);
        document.getElementById('newCharacterLabel').textContent = expectedNewName;
        
        // Reset transformation state
        document.getElementById('newCharacterImg').src = '/static/default-avatar.png';
        document.getElementById('newCharacterImg').className = 'placeholder';
        document.getElementById('newCharacterBox').className = 'character-box placeholder';
        document.getElementById('progressWave').style.width = '0%';
        document.getElementById('progressPercentSimple').textContent = '0%';
        document.getElementById('progressStatusSimple').textContent = 'Preparing transformation...';
        
        // Reset completion state - button starts disabled
        const completionDiv = document.getElementById('transformationComplete');
        const completionBtn = document.getElementById('chatWithNewCharacter');
        completionDiv.style.display = 'block';
        completionDiv.classList.remove('ready');
        completionBtn.classList.remove('active');
        
        // Show the modal
        document.getElementById('transformationModal').style.display = 'flex';
        
        // Start the transformation animation - but don't reach 100% automatically
        this.animateTransformationToAvatarGeneration();
    }

    extractCharacterNameFromChange(changeText) {
        // Try to extract character name from change description
        const namePatterns = [
            /you're now (\w+)/i,
            /become (\w+)/i,
            /you're (\w+)/i,
            /now (\w+)/i
        ];
        
        for (const pattern of namePatterns) {
            const match = changeText.match(pattern);
            if (match) {
                return match[1];
            }
        }
        
        return 'New Character';
    }

    async animateTransformationToAvatarGeneration() {
        console.log('🎬 Starting real-time progress tracking...');
        
        // Poll for real progress from the backend
        const pollProgress = async () => {
            try {
                const response = await fetch('/progress');
                if (response.ok) {
                    const progressData = await response.json();
                    const { progress, status, character_name } = progressData;
                    
                    console.log(`📊 Real progress: ${progress}% - ${status}`);
                    
                    // Update the progress bar with real data
                    await this.updateTimelineProgress(progress, status);
                    
                    // If transformation is complete (100%), stop polling
                    if (progress >= 100) {
                        console.log('🎯 Transformation complete - stopping progress polling');
                        return true; // Signal completion
                    }
                    
                    return false; // Continue polling
                } else {
                    console.warn('Failed to fetch progress, continuing to poll...');
                    return false;
                }
            } catch (error) {
                console.warn('Progress polling error:', error);
                return false; // Continue polling despite errors
            }
        };
        
        // Poll every 500ms for smooth updates
        const pollInterval = setInterval(async () => {
            const isComplete = await pollProgress();
            if (isComplete) {
                clearInterval(pollInterval);
            }
        }, 500);
        
        // Fallback: stop polling after 2 minutes to prevent infinite polling
        setTimeout(() => {
            clearInterval(pollInterval);
            console.log('🕐 Progress polling timeout - stopping');
        }, 120000);
    }

    async updateTimelineProgress(progress, status) {
        return new Promise(resolve => {
            // Update status text
            document.getElementById('progressStatusSimple').textContent = status;
            
            // Update progress bar
            document.getElementById('progressWave').style.width = `${progress}%`;
            document.getElementById('progressPercentSimple').textContent = `${progress}%`;
            
            console.log(`✅ Timeline Progress: ${status} (${progress}%)`);
            setTimeout(resolve, 100);
        });
    }

    async completeTransformation(characterName, newAvatar, reply) {
        console.log(`🎉 Completing transformation to ${characterName}`);
        
        // First, update progress to 100% now that we have the avatar
        await this.updateTimelineProgress(100, 'Finalizing transformation...');
        
        // Update the new character image and box
        const newCharacterImg = document.getElementById('newCharacterImg');
        const newCharacterBox = document.getElementById('newCharacterBox');
        
        // Load the new character image
        newCharacterImg.src = newAvatar;
        newCharacterImg.className = 'loaded';
        newCharacterBox.className = 'character-box loaded';
        
        // Update character name in timeline and completion button
        document.getElementById('newCharacterLabel').textContent = characterName;
        document.getElementById('finalCharacterName').textContent = characterName.toLowerCase();
        
        // Update progress status
        document.getElementById('progressStatusSimple').textContent = 'Transformation complete!';
        
        // Update the main character info
        this.updateCharacterAvatar(newAvatar, characterName);
        
        // Wait a moment for the image to load, then enable the completion section
        setTimeout(() => {
            const completionDiv = document.getElementById('transformationComplete');
            const completionBtn = document.getElementById('chatWithNewCharacter');
            
            completionDiv.classList.add('ready');
            completionBtn.classList.add('active');
            
            console.log('✅ Button activated - ready to start chat');
        }, 500); // Small delay to ensure image loads
        
        // Set up the completion button
        document.getElementById('chatWithNewCharacter').onclick = () => {
            this.finishTransformation(reply);
        };
    }

    finishTransformation(reply) {
        console.log('🔄 Finishing transformation and returning to chat...');
        
        // Hide transformation modal
        this.hideTransformationModal();
        
        // Add the transformation message to chat
        this.addUserMessage(`/change ${this.currentChangeText}`);
        this.addAssistantMessage(reply);
        this.addSystemMessage(`🎭 Transformed into ${this.currentCharacterName}!`);
        
        // Check if there was avatar generation info to show
        if (this.lastAvatarInfo) {
            this.addSystemMessage(`💡 ${this.lastAvatarInfo}`);
            this.lastAvatarInfo = null; // Clear it
        }
        
        // Clear the change input and stored text
        document.getElementById('changeInput').value = '';
        this.currentChangeText = null;
        
        console.log(`✅ Transformation complete! Now chatting with ${this.currentCharacterName}`);
    }

    hideTransformationModal() {
        document.getElementById('transformationModal').style.display = 'none';
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    updateCharacterAvatar(avatarUrl, characterName = null) {
        console.log(`🔄 Updating character avatar: ${avatarUrl}, name: ${characterName}`);
        
        this.currentAvatar = avatarUrl;
        if (characterName) {
            this.currentCharacterName = characterName;
            console.log(`📝 Character name updated to: ${this.currentCharacterName}`);
        }

        // Update all avatar images throughout the app
        const avatarElements = [
            'characterAvatar',
            'welcomeAvatar', 
            'typingAvatar'
        ];
        
        avatarElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.src = avatarUrl;
                element.alt = this.currentCharacterName;
                console.log(`✅ Updated ${elementId} with ${avatarUrl}`);
            } else {
                console.log(`❌ Element ${elementId} not found`);
            }
        });
        
        // Update all character name references
        const nameElements = [
            'characterName',
            'welcomeName'
        ];
        
        nameElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = this.currentCharacterName;
                console.log(`✅ Updated ${elementId} text to: ${this.currentCharacterName}`);
            } else {
                console.log(`❌ Element ${elementId} not found`);
            }
        });
        
        // Update page title
        document.title = `Chat with ${this.currentCharacterName}`;
        console.log(`✅ Updated page title to: Chat with ${this.currentCharacterName}`);
        
        // Update welcome description with character name
        const welcomeDesc = document.getElementById('welcomeDesc');
        if (welcomeDesc) {
            welcomeDesc.textContent = `Your AI companion ${this.currentCharacterName} is ready to chat! 💬`;
            console.log(`✅ Updated welcome description for ${this.currentCharacterName}`);
        }
        
        // Update help tip with character name
        const helpTip = document.getElementById('helpTip');
        if (helpTip) {
            helpTip.innerHTML = `💡 <strong>Tip:</strong> ${this.currentCharacterName} adapts to your conversation style and becomes more natural over time!`;
            console.log(`✅ Updated help tip for ${this.currentCharacterName}`);
        }
        
        // Log the final update
        console.log(`🎯 Character update complete: ${this.currentCharacterName} with avatar: ${avatarUrl}`);
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
                this.addSystemMessage('🗑️ Memory reset! Starting fresh...');
                
                // Force page refresh for completely clean state
                setTimeout(() => {
                    console.log('🔄 Refreshing page for fresh memory state...');
                    window.location.reload();
                }, 1000);
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