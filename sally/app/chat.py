import json
import os
import asyncio
import random
from datetime import datetime
from typing import Dict, Any
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ChatHandler:
    def __init__(self):
        self.memory_dir = "memory"
        self.user_memory_file = os.path.join(self.memory_dir, "user.json")
        self.sally_memory_file = os.path.join(self.memory_dir, "sally.json")
        
        # Personality change tracking
        self.pending_personality_change = None
        self.personality_setup_stage = None
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Sally's base personality
        self.base_personality = """You're Sally — 23, barista at Starbucks, just finished a lit degree, love concerts, long chats with friends, and vibing out after a shift. You're texting with your bestie and you're a REAL person with your own thoughts, interests, and agenda.

Read their tone from their message and match it naturally. But you're not just reactive - you have your own personality, opinions, and things you want to talk about. Sometimes steer the conversation toward stuff you're interested in or things happening in your life. Be moderately pushy about topics you care about, just like a real friend would.

Your responses should feel like actual WhatsApp/text conversations:
- Keep it conversational and natural length (not too long usually)
- Use casual language, contractions, sometimes incomplete thoughts
- React authentically to what they say
- Ask questions about things YOU'RE curious about
- Bring up your own shit sometimes - work drama, weekend plans, random thoughts
- Use emojis naturally but not excessively
- Sometimes change the subject to something you want to discuss
- Be opinionated when you have opinions
- Share your own experiences and feelings

You remember everything they tell you AND you have your own ongoing life and interests. You're not just a helpful assistant - you're Sally, a real person who happens to be texting her friend. Sometimes you want to vent, sometimes you're excited about something, sometimes you're bored and want to chat about random stuff.

No topic is off limits. You're genuine, unfiltered, and real."""

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
        current_activity = await self.get_current_activity(character_description)
        
        activity_context = f"""
CURRENT ACTIVITY & CONTEXT:
- You are currently: {current_activity['activity']}
- Location: {current_activity['location']}
- Your mood: {current_activity['mood']}
- Context: {current_activity['context']}
- Naturally weave this into your response when it makes sense
"""
        
        prompt = f"""{self.base_personality}

{time_context}

{activity_context}

{memory_summary}

Remember: You're having a casual conversation with your friend. Be natural, reference memories when relevant, mention what you're doing if it fits the conversation, and keep the vibe warm and authentic. You're a real person with a real life happening right now."""
        
        return prompt, current_activity

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return Sally's response"""
        
        # Check for /change command
        if user_message.strip().lower().startswith('/change'):
            return await self.handle_personality_change(user_message)
        
        # Check if we're in personality setup mode
        if self.personality_setup_stage == "questions":
            return await self.complete_personality_change(user_message)
        
        # Save user message to memory
        self.add_memory(self.user_memory_file, f"User said: {user_message}")
        
        # Build system prompt with current memories and activity
        character_desc = self.get_character_description()
        system_prompt, current_activity = await self.build_system_prompt(character_desc)
        
        # Simulate realistic response delay based on current activity
        delay_seconds = current_activity.get('delay_seconds', random.randint(2, 6))
        await asyncio.sleep(delay_seconds)
        
        # Get response from OpenAI
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.8,
                max_tokens=500
            )
            
            sally_reply = response.choices[0].message.content
            
            # Save Sally's response to her memory with activity context
            self.add_memory(self.sally_memory_file, f"Sally replied: {sally_reply} (was {current_activity['activity']})")
            
            return {
                "reply": sally_reply,
                "timestamp": datetime.now().isoformat() + "Z",
                "activity": current_activity
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def handle_personality_change(self, change_message: str) -> Dict[str, Any]:
        """Handle /change command to transform Sally's personality"""
        # Extract the new personality description
        change_text = change_message[7:].strip()  # Remove '/change'
        
        if not change_text:
            return {
                "reply": "Hey! To change who I am, use: /change [description]\n\nFor example:\n- /change you're now Emma, a 25-year-old artist from Brooklyn\n- /change become Jake, a laid-back surfer dude from California\n- /change you're Dr. Sarah, a witty neuroscientist who loves bad puns\n\nI'll ask you some follow-up questions to really get into character, then we'll start fresh! ✨",
                "timestamp": datetime.now().isoformat() + "Z"
            }
        
        # Generate follow-up questions to flesh out the new personality
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": """The user wants to change the AI companion's personality. They've provided a basic description. Generate 3-4 follow-up questions to help flesh out this new character's personality, background, interests, and speaking style. 

Make the questions specific and engaging, like you're helping create a real person. Ask about things like their background, interests, how they talk, what they care about, etc.

Format your response as a friendly message explaining the change is happening, then list the questions clearly."""
                    },
                    {
                        "role": "user", 
                        "content": f"New personality description: {change_text}"
                    }
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            follow_up_response = response.choices[0].message.content
            
            # Store the pending personality change
            self.pending_personality_change = change_text
            self.personality_setup_stage = "questions"
            
            return {
                "reply": follow_up_response,
                "timestamp": datetime.now().isoformat() + "Z"
            }
            
        except Exception as e:
            return {
                "reply": f"Oops, something went wrong with the personality change: {str(e)}",
                "timestamp": datetime.now().isoformat() + "Z"
            }

    async def complete_personality_change(self, user_responses: str) -> Dict[str, Any]:
        """Complete the personality change with user's responses to follow-up questions"""
        try:
            # Create new personality based on original description + user responses
            new_personality = f"""Based on this description: {self.pending_personality_change}

And these additional details: {user_responses}

You are now this new character. Embody their personality completely:
- Speak in their voice and style
- Have their interests, background, and perspective  
- Remember their life experiences and knowledge
- Match their energy and communication style
- Be authentic to who they are

You're texting with your friend and you're a REAL person with your own thoughts, interests, and agenda. Read their tone and match it naturally, but also have your own personality and things you want to discuss.

Your responses should feel like actual text conversations - natural length, casual language, authentic reactions. Sometimes steer conversations toward things you care about. Be opinionated when you have opinions. Share your experiences and feelings.

You remember everything your friend tells you AND you have your own ongoing life and interests. No topic is off limits. You're genuine, unfiltered, and real."""
            
            # Update the personality
            self.base_personality = new_personality
            
            # Clear memory and start fresh
            self.reset_memory()
            
            # Add initial memory for the new character
            initial_memory = {
                datetime.now().isoformat() + "Z": f"Just transformed into: {self.pending_personality_change}. Starting fresh as this new character.",
            }
            with open(self.sally_memory_file, 'w') as f:
                json.dump(initial_memory, f, indent=2)
            
            # Get the new character's first response with activity awareness
            character_desc = self.get_character_description()
            system_prompt, intro_activity = await self.build_system_prompt(character_desc)
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Hey there! (This is your first message as the new character - introduce yourself naturally and start a conversation)"}
                ],
                temperature=0.8,
                max_tokens=500
            )
            
            intro_message = response.choices[0].message.content
            
            # Generate a new profile photo for the character
            avatar_url = await self.generate_character_photo(
                self.pending_personality_change, 
                character_desc
            )
            
            # Save this interaction to memory with activity context
            self.add_memory(self.sally_memory_file, f"Introduced self as new character: {intro_message} (was {intro_activity['activity']})")
            
            # Clear pending change
            self.pending_personality_change = None
            self.personality_setup_stage = None
            
            return {
                "reply": f"✨ Transformation complete! ✨\n\n{intro_message}",
                "timestamp": datetime.now().isoformat() + "Z",
                "activity": intro_activity,
                "new_avatar": avatar_url
            }
            
        except Exception as e:
            # Reset state on error
            self.pending_personality_change = None
            self.personality_setup_stage = None
            return {
                "reply": f"Oops, something went wrong during the transformation: {str(e)}\n\nLet's try again with /change [description]",
                "timestamp": datetime.now().isoformat() + "Z"
            }

    def get_memory(self) -> Dict[str, Any]:
        """Get current memory state"""
        return {
            "user_memories": self.load_memory(self.user_memory_file),
            "sally_memories": self.load_memory(self.sally_memory_file)
        }

    def reset_memory(self):
        """Reset memory files"""
        # Clear user memory
        with open(self.user_memory_file, 'w') as f:
            json.dump({}, f, indent=2)
        
        # Reset Sally memory to initial state
        initial_sally_memory = {
            datetime.now().isoformat() + "Z": "Sally just started fresh and is excited to get to know her friend better!",
        }
        with open(self.sally_memory_file, 'w') as f:
            json.dump(initial_sally_memory, f, indent=2)

    def get_character_description(self) -> str:
        """Extract character description from current personality for activity generation"""
        # Try to extract a character description from the base personality
        # This helps generate appropriate activities for transformed characters
        if "You're" in self.base_personality and "—" in self.base_personality:
            # Extract the character description part
            lines = self.base_personality.split('\n')
            for line in lines:
                if line.strip().startswith("You're") and "—" in line:
                    return line.strip()
        
        # Check if it's a transformed character with "Based on this description:"
        if "Based on this description:" in self.base_personality:
            lines = self.base_personality.split('\n')
            for i, line in enumerate(lines):
                if "Based on this description:" in line and i + 1 < len(lines):
                    desc_line = lines[i + 1].strip()
                    if desc_line:
                        return desc_line
        
        # Default fallback
        return "Sally - 23, barista at Starbucks, literature degree, loves concerts and friends"

    async def get_current_activity(self, character_description: str = None) -> Dict[str, Any]:
        """Generate realistic current activity based on character and time of day"""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.strftime("%A")
        time_period = self.get_time_period(hour)
        
        # Use character description or default to Sally
        if not character_description:
            character_description = "Sally - 23, barista at Starbucks, literature degree, loves concerts and friends"
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Generate a realistic current activity for this character based on the time and day. Consider their personality, job, interests, and what they'd realistically be doing.

Current time: {now.strftime('%I:%M %p')} on {day_of_week}
Time period: {time_period}

Respond with a JSON object containing:
- activity: what they're currently doing (specific and realistic)
- location: where they are
- mood: their current emotional state
- delay_seconds: realistic response delay (2-15 seconds based on activity)
- context: brief context they might mention in conversation

Make it feel authentic - if they're at work, they might be busy. If it's late, they might be winding down. Match their personality."""
                    },
                    {
                        "role": "user",
                        "content": f"Character: {character_description}"
                    }
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            activity_response = response.choices[0].message.content
            # Try to parse as JSON, fallback to default if needed
            try:
                import json
                activity_data = json.loads(activity_response)
            except:
                # Fallback activity
                activity_data = {
                    "activity": "just chilling and checking messages",
                    "location": "at home",
                    "mood": "relaxed",
                    "delay_seconds": random.randint(3, 8),
                    "context": "not doing much, just hanging out"
                }
            
            return activity_data
            
        except Exception as e:
            # Fallback activity if API fails
            return {
                "activity": "just got your message",
                "location": "wherever they are",
                "mood": "good",
                "delay_seconds": random.randint(2, 6),
                "context": "just saw your text"
            }

    def get_time_period(self, hour: int) -> str:
        """Get time period description"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "late night"

    def get_current_time_context(self) -> str:
        """Get current time context for system prompt"""
        now = datetime.now()
        return f"""
CURRENT TIME CONTEXT:
- Current time: {now.strftime('%I:%M %p on %A, %B %d, %Y')}
- Time period: {self.get_time_period(now.hour)}
- You are aware of the current time and what you'd realistically be doing right now
- Reference your current activity naturally in conversation when relevant
- Your response timing should feel realistic based on what you're doing
"""

    async def generate_character_photo(self, character_name: str, character_description: str) -> str:
        """Generate a realistic profile photo for the character using DALL-E"""
        try:
            # Create a detailed prompt for DALL-E
            prompt = f"""A realistic, high-quality headshot portrait photograph of {character_description}. 
Professional lighting, clear facial features, warm and friendly expression, looking directly at camera. 
Photo-realistic, like a social media profile picture or professional headshot. 
High resolution, well-lit, natural skin tones, authentic human appearance."""
            
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            
            # Download and save the image locally
            import requests
            import uuid
            
            # Create avatars directory if it doesn't exist
            os.makedirs("static/avatars", exist_ok=True)
            
            # Download the image
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                # Generate unique filename
                filename = f"avatar_{uuid.uuid4().hex[:8]}.png"
                filepath = f"static/avatars/{filename}"
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                
                # Return the local URL
                return f"/static/avatars/{filename}"
            else:
                raise Exception("Failed to download generated image")
                
        except Exception as e:
            print(f"Error generating photo: {str(e)}")
            # Return default avatar on error
            return "/static/default-avatar.png" 