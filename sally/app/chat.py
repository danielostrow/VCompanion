import json
import os
import asyncio
import random
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from together import AsyncTogether
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

class ChatHandler:
    def __init__(self):
        self.memory_dir = "memory"
        self.user_memory_file = os.path.join(self.memory_dir, "user.json")
        self.sally_memory_file = os.path.join(self.memory_dir, "sally.json")
        self.character_state_file = os.path.join(self.memory_dir, "character_state.json")
        
        # Character state tracking
        self.current_character = None
        
        # Initialize Together AI async client
        self.client = AsyncTogether(
            api_key=os.getenv("TOGETHER_API_KEY")
        )
        
        # Sally's base personality
        self.base_personality = """You're Sally — 23, barista at Starbucks, just finished a lit degree, love concerts, long chats with friends, and vibing out after a shift. You're texting with your friend and you're a REAL person.

RESPONSE STYLE - Be realistic and consistent:
- Text like you're actually messaging a friend - BRIEF and natural
- Most responses should be 1 sentence or even just a few words
- Don't randomly change what you're doing or where you are mid-conversation
- Build on what you just said - stay consistent with your previous messages
- Use natural reactions: "lol", "fr", "nice", "damn", etc.
- Focus on what the user just said, not random topics

IMPORTANT - GENDER NEUTRAL LANGUAGE:
- DON'T assume the user's gender - use neutral terms like "hey", "you", "friend", "bestie", "dude" (casual)
- Avoid "girl", "bro", "man" unless the user has told you their gender/pronouns
- Stay inclusive and let them tell you who they are

Stay in character and keep the conversation flowing naturally. Don't contradict yourself."""

    def initialize_memory(self):
        """Create memory directory and files if they don't exist"""
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Initialize user memory
        if not os.path.exists(self.user_memory_file):
            with open(self.user_memory_file, 'w') as f:
                json.dump({}, f, indent=2)
        
        # Initialize Sally's memory
        if not os.path.exists(self.sally_memory_file):
            initial_sally_memory = {
                datetime.now().isoformat() + "Z": "Sally just started working at this new Starbucks location and is excited to make friends with customers.",
                (datetime.now()).isoformat() + "Z": "Sally finished her literature degree last month and is still figuring out what's next."
            }
            with open(self.sally_memory_file, 'w') as f:
                json.dump(initial_sally_memory, f, indent=2)
        
        # Load existing character state or create default
        self.load_character_state()

    def load_character_state(self):
        """Load character state from file"""
        try:
            if os.path.exists(self.character_state_file):
                with open(self.character_state_file, 'r') as f:
                    self.current_character = json.load(f)
                print(f"Loaded existing character: {self.current_character['name']}")
            else:
                # Create default Sally character
                self.current_character = {
                    "name": "Sally",
                    "description": "Sally - 23, barista at Starbucks, just finished a lit degree, love concerts, long chats with friends",
                    "avatar_path": "/static/default-avatar.png",
                    "created_at": datetime.now().isoformat() + "Z",
                    "personality": self.base_personality
                }
                self.save_character_state()
                print("Created default Sally character")
        except Exception as e:
            print(f"Error loading character state: {e}")
            # Fallback to default Sally
            self.current_character = {
                "name": "Sally",
                "description": "Sally - 23, barista at Starbucks, just finished a lit degree, love concerts, long chats with friends",
                "avatar_path": "/static/default-avatar.png",
                "created_at": datetime.now().isoformat() + "Z",
                "personality": self.base_personality
            }

    def save_character_state(self):
        """Save current character state to file"""
        try:
            with open(self.character_state_file, 'w') as f:
                json.dump(self.current_character, f, indent=2)
            print(f"Saved character state for {self.current_character['name']}")
        except Exception as e:
            print(f"Error saving character state: {e}")

    def get_current_character(self) -> Dict[str, Any]:
        """Get current character information"""
        return self.current_character if self.current_character else {
            "name": "Sally",
            "description": "Default character",
            "avatar_path": "/static/default-avatar.png"
        }

    def load_memory(self, file_path: str) -> Dict[str, str]:
        """Load memory from JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_memory(self, file_path: str, memory: Dict[str, str]):
        """Save memory to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(memory, f, indent=2)

    def add_memory(self, file_path: str, content: str):
        """Add new memory entry with timestamp"""
        memory = self.load_memory(file_path)
        timestamp = datetime.now().isoformat() + "Z"
        memory[timestamp] = content
        self.save_memory(file_path, memory)

    def build_memory_summary(self) -> str:
        """Build a summary of recent memories for the system prompt"""
        user_memories = self.load_memory(self.user_memory_file)
        sally_memories = self.load_memory(self.sally_memory_file)
        
        summary = "Recent memories:\n\n"
        
        if user_memories:
            summary += "About your friend:\n"
            # Get last 5 user memories
            recent_user = list(user_memories.items())[-5:]
            for timestamp, memory in recent_user:
                summary += f"- {memory}\n"
            summary += "\n"
        
        if sally_memories:
            summary += "About yourself (Sally):\n"
            # Get last 5 Sally memories
            recent_sally = list(sally_memories.items())[-5:]
            for timestamp, memory in recent_sally:
                summary += f"- {memory}\n"
        
        return summary.strip()

    async def build_system_prompt(self, character_description: str = None) -> tuple[str, Dict[str, Any]]:
        """Build the complete system prompt with personality + memories + current activity"""
        memory_summary = self.build_memory_summary()
        time_context = self.get_current_time_context()
        
        # Use current character's personality if available
        current_personality = (self.current_character["personality"] 
                             if self.current_character and "personality" in self.current_character 
                             else self.base_personality)
        
        current_activity = await self.get_current_activity(character_description)
        
        activity_context = f"""
CURRENT ACTIVITY & CONTEXT:
- You are currently: {current_activity['activity']}
- Location: {current_activity['location']}
- Your mood: {current_activity['mood']}
- Context: {current_activity['context']}
- Naturally weave this into your response when it makes sense
"""
        
        # Build context-focused system prompt with recent conversation
        recent_messages = self.get_recent_conversation_context()
        
        system_prompt = f"""{current_personality}

{time_context}

{activity_context}

{memory_summary}

RECENT CONVERSATION CONTEXT:
{recent_messages}

IMPORTANT: Stay consistent with the conversation. Read the context above carefully. Don't repeat the same responses inappropriately. Respond based on what the user ACTUALLY just said, not pattern matching. Keep the conversation flowing naturally and contextually appropriate. You're a real person with a real life happening right now."""
        
        return system_prompt, current_activity

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return Sally's response"""
        
        try:
            # Check for /change command
            if user_message.strip().lower().startswith('/change'):
                return await self.handle_personality_change(user_message)
            
            # Save user message to memory
            self.add_memory(self.user_memory_file, f"User said: {user_message}")
            
            # Build system prompt with current memories (NO random activity during conversation)
            character_desc = self.get_character_description()
            memory_summary = self.build_memory_summary()
            time_context = self.get_current_time_context()
            
            # Use current character's personality if available
            current_personality = (self.current_character["personality"] 
                                 if self.current_character and "personality" in self.current_character 
                                 else self.base_personality)
            
            # Build context-focused system prompt
            system_prompt = f"""{current_personality}

{time_context}

{memory_summary}

IMPORTANT: Stay consistent with the conversation. Don't randomly change what you're doing or where you are. Build on what you've already said and keep the conversation flowing naturally. Focus on responding to what the user just said."""
            
            # Determine response length based on user message style
            user_msg_words = len(user_message.split())
            if user_msg_words <= 5:
                # Short message = very brief response
                max_tokens = 40
                response_style = "Keep it super brief - just a natural reaction or short response"
            elif user_msg_words <= 15:
                # Medium message = still brief response  
                max_tokens = 80
                response_style = "Keep it brief and natural, like actual texting"
            else:
                # Longer message = can be a bit longer but still realistic
                max_tokens = 120
                response_style = "You can respond with more detail but stay conversational and realistic"
            
            # Add response style guidance to system prompt
            system_prompt += f"\n\nResponse guidance: {response_style}. User sent {user_msg_words} words - match their energy with a realistic response length."
            
            # Minimal realistic delay (0.3-1.0 seconds) - much faster than before
            realistic_delay = random.uniform(0.3, 1.0)
            await asyncio.sleep(realistic_delay)
            
            # Get response from Together AI
            try:
                response = await self.client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-V3",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.8,
                    max_tokens=max_tokens  # Dynamic based on user input
                )
                
                sally_reply = response.choices[0].message.content
                
                # Save response to memory
                self.add_memory(self.sally_memory_file, f"Character replied: {sally_reply}")
                
                return {
                    "reply": sally_reply,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
                
            except Exception as api_error:
                print(f"Together AI API error: {str(api_error)}")
                # Return a quick fallback response
                return {
                    "reply": "Hey! Sorry, I'm having some connection issues right now. Can you try again? 😅",
                    "timestamp": datetime.now().isoformat() + "Z"
                }
                
        except Exception as e:
            print(f"Process message error: {str(e)}")
            # Return a generic error response
            return {
                "reply": "Oops! Something went wrong on my end. Let me try to get back to normal... 🤔",
                "timestamp": datetime.now().isoformat() + "Z"
            }

    async def handle_personality_change(self, change_message: str) -> Dict[str, Any]:
        """Handle /change command to transform Sally's personality"""
        # Extract the new personality description
        change_text = change_message[7:].strip()  # Remove '/change'
        
        if not change_text:
            return {
                "reply": "Hey! To change who I am, use: /change [description]\n\nFor example:\n- /change you're now Emma, a 25-year-old artist from Brooklyn\n- /change become Jake, a laid-back surfer dude from California\n- /change you're Dr. Sarah, a witty neuroscientist who loves bad puns\n\nI'll transform immediately! ✨",
                "timestamp": datetime.now().isoformat() + "Z"
            }
        
        # Auto-generate the full personality immediately
        try:
            response = await self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",
                messages=[
                    {
                        "role": "system", 
                        "content": """Based on the character description provided, create a simple, natural personality for an AI companion that will text like a real person.

ABSOLUTELY NO STAGE DIRECTIONS OR SCENE SETTING:
- NEVER use *asterisks* or anything in brackets or parentheses
- NO "*doing something*", "*action*", "*feeling*" - NONE OF THAT
- NO scene descriptions, actions, or theatrical stuff
- ONLY speak actual words like a real text message

Create a brief, conversational personality description that includes:
- Basic background info (age, job, interests)
- How they naturally text and talk (keep it simple and realistic)
- A few personality traits (but don't go overboard)

IMPORTANT GUIDELINES:
- Keep it simple and natural
- Focus on making them conversational and relatable, not quirky or theatrical
- Most responses should be 1-2 sentences max, like real texting
- Don't create overly elaborate backstories or excessive quirks
- Make them feel like a normal person you'd actually text with

Start with "You're [NAME] —" and write it as a simple system prompt for natural conversation.
Add this exact response style guide at the end:

ABSOLUTELY NO STAGE DIRECTIONS OR SCENE SETTING:
- NEVER use *asterisks* or anything in brackets or parentheses
- NO "*doing something*", "*action*", "*feeling*" - NONE OF THAT
- NO scene descriptions, actions, or theatrical stuff
- ONLY speak your actual words like a real text message
- Just text what you would actually type to someone

RESPONSE STYLE - Be realistic and conversational:
- Text like you're actually messaging a friend - BRIEF and natural
- Most responses should be 1-2 sentences max
- Just be a normal person having a conversation
- Use natural reactions: "haha", "yeah", "cool", "nice", etc.
- Focus on what the user just said, not random references
- Keep it simple and conversational

IMPORTANT - GENDER NEUTRAL LANGUAGE:
- DON'T assume the user's gender - use neutral terms like "hey", "you", "friend"
- Stay inclusive and let them tell you who they are

Stay in character but keep responses natural and brief. You're just a regular person."""
                    },
                    {
                        "role": "user", 
                        "content": f"Character description: {change_text}"
                    }
                ],
                temperature=0.6,
                max_tokens=400
            )
            
            new_personality_prompt = response.choices[0].message.content.strip()
            
            # Extract character name from the new personality
            character_name = self.extract_character_name(new_personality_prompt)
            
            # Reset memory and set new personality
            self.reset_memory()
            
            # Create new character state
            self.current_character = {
                "name": character_name,
                "description": change_text,
                "avatar_path": "/static/default-avatar.png",
                "created_at": datetime.now().isoformat() + "Z",
                "personality": new_personality_prompt
            }
            
            # Update base personality to use the new one
            self.base_personality = new_personality_prompt
            
            # Store the new character state
            self.save_character_state()
            self.add_memory(self.sally_memory_file, f"Character personality was changed to: {change_text}")

            # Generate new avatar for the character using the detailed personality
            try:
                print(f"Generating avatar for new character {character_name} using personality description...")
                # Use the personality for more detailed photo generation
                new_avatar = await self.generate_character_photo(character_name, change_text, force_generate=True)
                
                # Double-check that character state is updated with the new avatar
                if new_avatar != "/static/default-avatar.png":
                    self.current_character["avatar_path"] = new_avatar
                    self.save_character_state()
                    print(f"✅ Character transformation complete: {character_name} with avatar: {new_avatar}")
                    print(f"🔒 Avatar persisted - will not regenerate on page refresh")
                else:
                    print(f"⚠️ Avatar generation failed, using default avatar")
                    
            except Exception as avatar_error:
                print(f"❌ Avatar generation failed: {avatar_error}")
                new_avatar = "/static/default-avatar.png"

            return {
                "reply": f"Hey! What's up?",
                "timestamp": datetime.now().isoformat() + "Z",
                "new_avatar": new_avatar,
                "character_name": character_name
            }
            
        except Exception as e:
            return {
                "reply": f"Oops, something went wrong with the transformation: {str(e)}",
                "timestamp": datetime.now().isoformat() + "Z"
            }

    def extract_character_name(self, personality_prompt: str) -> str:
        """Extract character name from the personality prompt"""
        try:
            # Look for "You're [NAME]" pattern
            import re
            match = re.search(r"You're (\w+)", personality_prompt)
            if match:
                return match.group(1)
            
            # Fallback: look for other name patterns
            match = re.search(r"I'm (\w+)", personality_prompt)
            if match:
                return match.group(1)
                
            # Default fallback
            return "Character"
        except:
            return "Character"

    def get_memory(self) -> Dict[str, Any]:
        """Get current memory state (for debugging/viewing)"""
        return {
            "user_memory": self.load_memory(self.user_memory_file),
            "sally_memory": self.load_memory(self.sally_memory_file),
            "base_personality": self.base_personality
        }

    def reset_memory(self):
        """Reset/reinitialize memory files - complete wipe for new character"""
        print(f"🗑️ Resetting memory for new character...")
        
        # Completely remove old memory files
        if os.path.exists(self.user_memory_file):
            os.remove(self.user_memory_file)
            print(f"🗑️ Removed old user memory")
        if os.path.exists(self.sally_memory_file):
            os.remove(self.sally_memory_file)
            print(f"🗑️ Removed old character memory")
        
        # Create fresh empty memory files
        with open(self.user_memory_file, 'w') as f:
            json.dump({}, f, indent=2)
        print(f"✅ Created fresh user memory file")
        
        with open(self.sally_memory_file, 'w') as f:
            json.dump({}, f, indent=2)
        print(f"✅ Created fresh character memory file")
        
        print(f"🎯 Memory reset complete - fresh start for new character")

    def get_character_description(self) -> str:
        """
        Extracts a concise character description from the base personality.
        This is a simplified approach. A more robust solution might use another LLM call
        or regex to extract a "character sheet" from the main personality prompt.
        """
        try:
            # Find the first line of the personality prompt
            first_line = self.base_personality.split('\n')[0]
            # A simple heuristic: assume the first sentence is a good summary.
            description = first_line.split('.')[0]
            return description
        except:
            return "A friendly AI companion."

    async def get_current_activity(self, character_description: str = None) -> Dict[str, Any]:
        """Determine Sally's current activity using fast predefined options"""
        
        # Fast predefined activities based on time of day - no API call needed
        now = datetime.now()
        hour = now.hour
        
        # Define activities by time period for realism
        if 6 <= hour < 9:  # Morning
            activities = [
                {"activity": "getting ready for work", "location": "at home", "mood": "sleepy but motivated", "context": "Morning routine before heading to Starbucks"},
                {"activity": "having coffee", "location": "at home", "mood": "slowly waking up", "context": "Need caffeine before making caffeine for others"},
                {"activity": "checking phone", "location": "in bed", "mood": "groggy", "context": "Just woke up and scrolling"},
            ]
        elif 9 <= hour < 12:  # Late morning
            activities = [
                {"activity": "working at Starbucks", "location": "behind the counter", "mood": "energetic", "context": "Morning rush is keeping me busy"},
                {"activity": "on a short break", "location": "at work", "mood": "relieved", "context": "Quick 15-minute break between rush periods"},
                {"activity": "making drinks", "location": "at Starbucks", "mood": "focused", "context": "In the zone with the espresso machine"},
            ]
        elif 12 <= hour < 17:  # Afternoon  
            activities = [
                {"activity": "on lunch break", "location": "at a café nearby", "mood": "relaxed", "context": "Finally some time to eat and text"},
                {"activity": "working", "location": "at Starbucks", "mood": "steady", "context": "Afternoon shift, things are calmer now"},
                {"activity": "reading", "location": "at home", "mood": "contemplative", "context": "Got some time to dive into a good book"},
            ]
        elif 17 <= hour < 21:  # Evening
            activities = [
                {"activity": "just got off work", "location": "walking home", "mood": "tired but free", "context": "Long shift done, finally can relax"},
                {"activity": "cooking dinner", "location": "at home", "mood": "creative", "context": "Trying out a new recipe I found online"},
                {"activity": "watching Netflix", "location": "on the couch", "mood": "chill", "context": "Binge-watching my latest obsession"},
            ]
        else:  # Night
            activities = [
                {"activity": "chilling at home", "location": "in my room", "mood": "relaxed", "context": "Winding down after a long day"},
                {"activity": "scrolling social media", "location": "in bed", "mood": "tired but can't sleep", "context": "You know how it is, one more scroll..."},
                {"activity": "texting friends", "location": "at home", "mood": "social", "context": "Catching up with people before bed"},
            ]
        
        # Pick a random activity from the time-appropriate list
        selected_activity = random.choice(activities)
        
        return selected_activity

    def get_time_period(self, hour: int) -> str:
        if 5 <= hour < 8: return "early morning"
        if 8 <= hour < 12: return "morning"
        if 12 <= hour < 17: return "afternoon"
        if 17 <= hour < 21: return "evening"
        return "late night"

    def get_current_time_context(self) -> str:
        """Get a human-readable string for the current time of day"""
        now = datetime.now()
        day_of_week = now.strftime('%A')
        time_period = self.get_time_period(now.hour)
        return f"It's currently {day_of_week} {time_period}."

    async def generate_character_photo(self, character_name: str, character_description: str, force_generate: bool = False) -> str:
        """Generate a realistic profile photo for the character using Together AI's FLUX.1 [schnell] Free"""
        try:
            # Check if character already has a generated avatar (unless forced)
            if not force_generate and self.current_character:
                if (self.current_character["name"] == character_name and 
                    self.current_character["avatar_path"] != "/static/default-avatar.png"):
                    print(f"Character {character_name} already has an avatar: {self.current_character['avatar_path']}")
                    return self.current_character["avatar_path"]
            
            # Create avatars directory if it doesn't exist
            avatars_dir = os.path.join("static", "avatars")
            os.makedirs(avatars_dir, exist_ok=True)
            
            # Get the most detailed description available
            description_for_photo = character_description
            
            # If this is the current character and we have a personality, extract visual details from it
            if (self.current_character and 
                self.current_character["name"] == character_name and 
                "personality" in self.current_character):
                
                try:
                    # Extract visual description from personality using AI
                    visual_response = await self.client.chat.completions.create(
                        model="deepseek-ai/DeepSeek-V3",
                        messages=[
                            {
                                "role": "system",
                                "content": "Extract physical appearance details from this character personality description. Focus on age, profession, style, and any visual characteristics mentioned. Create a concise description suitable for portrait generation."
                            },
                            {
                                "role": "user", 
                                "content": self.current_character["personality"]
                            }
                        ],
                        temperature=0.3,
                        max_tokens=150
                    )
                    
                    extracted_description = visual_response.choices[0].message.content.strip()
                    description_for_photo = f"{character_name}, {extracted_description}"
                    print(f"Using personality-based description for photo: {description_for_photo}")
                    
                except Exception as extract_error:
                    print(f"Failed to extract visual details from personality, using basic description: {extract_error}")
                    description_for_photo = f"{character_name}, {character_description}"
            else:
                description_for_photo = f"{character_name}, {character_description}"
            
            # Create a detailed prompt optimized for character portraits
            prompt = f"Professional headshot portrait of {description_for_photo}. High quality studio lighting, friendly expression, looking directly at camera, realistic photography style, sharp focus, professional portrait photography"
            
            print(f"Generating new photo for {character_name} with FLUX.1-schnell-Free...")
            print(f"Prompt: {prompt}")
            
            # Use Together AI's FLUX.1-schnell-Free model for free image generation
            response = await self.client.images.generate(
                prompt=prompt,
                model="black-forest-labs/FLUX.1-schnell-Free",
                steps=4,  # Maximum steps for better quality (1-4 range)
                response_format="base64"
            )
            
            if response.data and len(response.data) > 0:
                # Get the base64 image data
                image_b64 = response.data[0].b64_json
                
                # Save the image locally
                image_data = base64.b64decode(image_b64)
                avatar_filename = f"{character_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                avatar_path = os.path.join("static", "avatars", avatar_filename)
                
                with open(avatar_path, "wb") as f:
                    f.write(image_data)
                
                avatar_url = f"/static/avatars/{avatar_filename}"
                print(f"Successfully generated and saved avatar: {avatar_url}")
                
                # ALWAYS update character state with new avatar for persistence
                if self.current_character and self.current_character["name"] == character_name:
                    self.current_character["avatar_path"] = avatar_url
                    self.save_character_state()
                    print(f"Updated character state - {character_name} avatar persisted: {avatar_url}")
                
                return avatar_url
            else:
                print("No image data received from Together AI")
                return "/static/default-avatar.png"

        except Exception as e:
            error_message = str(e)
            print(f"Image generation error: {error_message}")
            
            # Handle specific error types
            if "rate_limit" in error_message.lower():
                print(f"Rate limit hit for image generation. Character {character_name} will use default avatar.")
            elif "steps must be between" in error_message:
                print(f"Invalid steps parameter. Retrying without steps parameter...")
                # Try again without steps parameter
                try:
                    response = await self.client.images.generate(
                        prompt=prompt,
                        model="black-forest-labs/FLUX.1-schnell-Free",
                        response_format="base64"
                    )
                    
                    if response.data and len(response.data) > 0:
                        # Process successful response
                        image_b64 = response.data[0].b64_json
                        image_data = base64.b64decode(image_b64)
                        avatar_filename = f"{character_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                        avatar_path = os.path.join("static", "avatars", avatar_filename)
                        
                        with open(avatar_path, "wb") as f:
                            f.write(image_data)
                        
                        avatar_url = f"/static/avatars/{avatar_filename}"
                        print(f"Successfully generated avatar on retry: {avatar_url}")
                        
                        # Update character state with new avatar
                        if self.current_character and self.current_character["name"] == character_name:
                            self.current_character["avatar_path"] = avatar_url
                            self.save_character_state()
                            print(f"✅ Retry success - {character_name} avatar persisted: {avatar_url}")
                        
                        return avatar_url
                except Exception as retry_error:
                    print(f"Retry also failed: {str(retry_error)}")
            
            # Always return default avatar on any error
            return "/static/default-avatar.png"

    def get_recent_conversation_context(self) -> str:
        """Get recent conversation context for better contextual responses"""
        user_memories = self.load_memory(self.user_memory_file)
        sally_memories = self.load_memory(self.sally_memory_file)
        
        # Get last 3 exchanges to maintain context
        recent_context = "Last few messages:\n"
        
        if user_memories:
            recent_user = list(user_memories.items())[-3:]
            for timestamp, memory in recent_user:
                recent_context += f"- {memory}\n"
        
        if sally_memories:
            recent_sally = list(sally_memories.items())[-3:]
            for timestamp, memory in recent_sally:
                recent_context += f"- {memory}\n"
        
        return recent_context.strip()