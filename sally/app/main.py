from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
from typing import Dict, Any
from chat import ChatHandler
import base64
import requests

app = FastAPI(title="Sally - AI Companion Chatbot", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize chat handler
chat_handler = ChatHandler()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    timestamp: str

class PhotoRequest(BaseModel):
    character_name: str
    character_description: str

@app.on_event("startup")
async def startup_event():
    """Initialize memory files on startup"""
    chat_handler.initialize_memory()

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Serve the web chat interface"""
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Chat interface not found</h1>", status_code=404)

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Send a message to Sally and get her response"""
    try:
        response = await chat_handler.process_message(chat_message.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/generate_photo")
async def generate_photo(photo_request: PhotoRequest):
    """Generate a realistic profile photo for the character"""
    try:
        avatar_url = await chat_handler.generate_character_photo(
            photo_request.character_name, 
            photo_request.character_description
        )
        return {"avatar_url": avatar_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo generation error: {str(e)}")

@app.get("/memory")
async def get_memory():
    """Get current memory state (for debugging/viewing)"""
    try:
        memory = chat_handler.get_memory()
        return memory
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory error: {str(e)}")

@app.post("/reset")
async def reset_memory():
    """Reset/reinitialize memory files"""
    try:
        chat_handler.reset_memory()
        return {"message": "Memory reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 