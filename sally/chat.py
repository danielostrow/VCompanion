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
