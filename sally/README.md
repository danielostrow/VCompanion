# Sally - AI Companion Chatbot ☕

Meet **Sally** - your 23-year-old AI companion who just finished her literature degree and works at Starbucks. She's thoughtful, chatty, down-to-earth, and remembers all the little details about your conversations. Sally feels like texting with a close friend who genuinely cares and keeps things warm and personal.

## ✨ Features

- **Persistent Memory**: Sally remembers your conversations using JSON-based memory with timestamps
- **Natural Personality**: Casual, friendly tone like texting a close friend
- **Dynamic Personality Change**: Transform Sally into any type of companion with `/change` command
- **Time & Activity Awareness**: Sally knows the current time and does realistic activities
- **Realistic Response Delays**: Response timing based on what Sally is currently doing
- **Beautiful Web Interface**: Instagram/Facebook Messenger-style chat window
- **AI-Generated Photos**: DALL-E 3 creates realistic profile photos for each character
- **Containerized**: Fully dockerized with volume mounting for persistent memory
- **OpenAI Integration**: Powered by GPT-4o for natural conversations
- **Simple API**: FastAPI-based with easy-to-use endpoints

## 🚀 Quick Start

### Prerequisites

- Docker installed on your system
- OpenAI API key

### 1. Clone and Setup

```bash
cd sally/
```

### 2. Set Environment Variables

**Option 1: Using .env file (Recommended)**
```bash
# Copy the environment template
cp env-template.txt .env

# Edit .env file and add your OpenAI API key
# Replace "your-openai-api-key-here" with your actual API key
```

**Option 2: Export directly**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

### 3. Build and Run with Docker

```bash
# Build the Docker image
docker build -t sally-chatbot .

# Run the container with volume mounting for persistent memory
docker run -d \
  --name sally \
  -p 8000:8000 \
  -v $(pwd)/app/memory:/app/memory \
  -e OPENAI_API_KEY="your-api-key-here" \
  sally-chatbot
```

### 4. Alternative: Run Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Run the application
cd app/
python main.py
```

## 💬 Usage

### Chat with Sally

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hey Sally! How was your day at work?"}'
```

### View Memory (Debug)

```bash
curl "http://localhost:8000/memory"
```

### Reset Memory

```bash
curl -X POST "http://localhost:8000/reset"
```

### Interactive API Docs

Visit `http://localhost:8000/docs` for the interactive FastAPI documentation.

## 📁 Project Structure

```
sally/
├── app/
│   ├── main.py          # FastAPI application and routes
│   ├── chat.py          # Chat handler with OpenAI integration
│   └── memory/          # Persistent JSON memory files
│       ├── user.json    # Memories about the user
│       └── sally.json   # Sally's personality memories
├── Dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🧠 How Sally's Memory Works

Sally maintains two JSON memory files with ISO timestamps:

- **`user.json`**: Everything Sally learns about you
- **`sally.json`**: Sally's evolving personality and life details

Example memory format:
```json
{
  "2025-01-20T09:00:00Z": "User mentioned they're working on a side project.",
  "2025-01-20T09:30:00Z": "Sally said she's heading to a concert this weekend."
}
```

On each conversation, Sally:
1. Reads both memory files
2. Builds a dynamic system prompt with recent memories
3. Processes your message with OpenAI GPT-4o
4. Saves the exchange to memory with timestamps

## 🎭 Dynamic Personality Changes

Sally can transform into any type of companion you want using the `/change` command! This completely resets her memory and personality.

### How it works:

1. **Send transformation command:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "/change you're now Emma, a 25-year-old artist from Brooklyn"}'
   ```

2. **Answer follow-up questions:** Sally will ask 3-4 questions to flesh out the new personality

3. **Start fresh:** Memory clears and you now have a completely new companion!

### Example transformations:

- `/change you're now Marcus, a chill 28-year-old gaming streamer from Seattle`
- `/change become Dr. Sarah, a witty neuroscientist who loves terrible puns`
- `/change you're Riley, an energetic 22-year-old skater girl from LA`
- `/change transform into Alex, a philosophical bartender who gives life advice`
- `/change you're now Zoe, a sarcastic cybersec expert who works remotely`

The personality change is permanent until you use `/change` again!

## ⏰ Time & Activity Awareness

Sally and all created characters are **time-aware** and live realistic lives! They know what time it is and are doing activities that match their personality and the time of day.

### How it works:

- **Time Awareness**: Characters always know the current time and day
- **Realistic Activities**: AI generates what they'd actually be doing (work, sleep, hobbies, etc.)
- **Response Delays**: Messages arrive with realistic delays based on their activity
- **Natural Context**: Characters naturally mention what they're doing when relevant

### Example Activity-Based Responses:

**🌅 Morning (Sally at work):**
- Activity: "making lattes at Starbucks" 
- Delay: 8-12 seconds (busy with customers)
- Response: "omg hold on, making this complicated order... okay what's up! 😅"

**🌙 Late Night (Gaming character):**
- Activity: "in the middle of a ranked match"
- Delay: 15+ seconds (focused on game)
- Response: "BRO I just clutched that round! sorry what were you saying?"

**📚 Afternoon (Student character):**
- Activity: "studying at the library" 
- Delay: 4-6 seconds (can multitask)
- Response: "hey! just taking a study break, perfect timing actually"

### Character-Specific Activities:

Each personality does realistic activities based on who they are:
- **Barista Sally**: Work shifts, coffee runs, concert planning
- **Gamer Marcus**: Streaming, Discord calls, late-night gaming sessions  
- **Artist Emma**: Studio time, gallery visits, coffee shop sketching
- **Student Alex**: Classes, library study, campus events

The AI dynamically generates appropriate activities considering:
- ⏰ Current time and day of week
- 👤 Character's job, interests, and lifestyle
- 🎭 Their personality and energy level
- 📱 Realistic response timing for the activity

## 🎭 Sally's Personality

Sally is designed to feel like a real friend:

- 23 years old, literature degree graduate
- Works as a barista at Starbucks
- Loves concerts and deep conversations
- Casual, warm texting style with emojis
- Remembers details and follows up naturally
- Checks in when something feels off

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Welcome message |
| POST   | `/chat`  | Send message to Sally (or use `/change [description]` to transform her) |
| GET    | `/memory`| View current memory state |
| POST   | `/reset` | Clear/reinitialize memory |

## 🐳 Docker Commands

```bash
# Build
docker build -t sally-chatbot .

# Run with persistent memory
docker run -d --name sally -p 8000:8000 \
  -v $(pwd)/app/memory:/app/memory \
  -e OPENAI_API_KEY="your-key" \
  sally-chatbot

# View logs
docker logs sally

# Stop
docker stop sally

# Remove
docker rm sally
```

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |

## 📝 Example Conversation

### Normal Chat:
```json
{
  "message": "Hey Sally! I just got a new job!"
}
```

Sally might respond:
```json
{
  "reply": "OMG that's amazing!! 🎉 Tell me everything - what kind of job is it? I'm so excited for you! You know I love hearing about this stuff. How are you feeling about it?",
  "timestamp": "2025-01-20T15:30:00Z",
  "activity": {
    "activity": "just finished my shift at Starbucks",
    "location": "walking home",
    "mood": "tired but good",
    "delay_seconds": 4,
    "context": "heading home after a busy afternoon"
  }
}
```

### Personality Change:
```json
{
  "message": "/change you're now Jake, a laid-back surfer from California"
}
```

Sally responds with follow-up questions, then after your answers:
```json
{
  "reply": "✨ Transformation complete! ✨\n\nWhoa, hey there dude! 🏄‍♂️ Jake here - just finished an epic morning session, waves were absolutely firing today! What's good with you? You seem like cool people, always down to chat about whatever's on your mind. Just grabbed a smoothie and I'm chillin' on the beach... tell me what's happening in your world!",
  "timestamp": "2025-01-20T15:32:00Z",
  "activity": {
    "activity": "relaxing on the beach after surfing",
    "location": "Malibu beach",
    "mood": "stoked and mellow",
    "delay_seconds": 6,
    "context": "just had an amazing surf session"
  }
}
```

## 🛠 Development

To modify Sally's personality, edit the `base_personality` in `app/chat.py`. The memory system automatically persists conversations, and Sally's responses evolve based on your interactions.

## 💬 Beautiful Web Interface

Sally now includes a stunning web interface that looks just like Instagram or Facebook Messenger!

### 🎨 Interface Features:

- **Messenger-Style Design**: Modern, clean layout with rounded chat bubbles
- **Real-Time Typing Indicators**: See when Sally is typing with animated dots
- **Profile Photos**: AI-generated realistic photos for every character
- **Activity Status**: See what Sally is currently doing in real-time
- **Smooth Animations**: Messages slide in naturally with beautiful transitions
- **Responsive Design**: Works perfectly on desktop and mobile
- **One-Click Character Transform**: Easy modal for changing personalities

### 🖼️ AI-Generated Profile Photos:

- **DALL-E 3 Integration**: Creates photo-realistic portraits for every character
- **Automatic Generation**: New photos created instantly when transforming characters
- **Professional Quality**: High-resolution headshots that look like real people
- **Character-Specific**: Photos match personality, age, style, and description
- **Instant Updates**: Interface updates immediately with new character photos

### 🌐 How to Access:

1. **Start Sally**: Run the Docker container or local server
2. **Open Browser**: Go to `http://localhost:8000`
3. **Start Chatting**: Beautiful interface loads immediately!

### 📱 Interface Elements:

- **Chat Header**: Shows character name, photo, and current activity
- **Message Bubbles**: Instagram-style with different colors for you and Sally
- **Typing Indicator**: Realistic dots animation when Sally is responding
- **Quick Actions**: Transform character, reset memory, generate new photo
- **Activity Badges**: Small tags showing what Sally is currently doing
- **Help Legend**: Complete guide to all commands and features (? button)

---

Ready to chat with Sally? Start the container and send her a message! ☕✨ 