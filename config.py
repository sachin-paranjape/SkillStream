import os
from dotenv import load_dotenv
from google import genai
from openai import OpenAI as LocalAI

load_dotenv()

# --- PATHS ---
DATA_PATH = "data/interactions.csv"
os.makedirs("data", exist_ok=True)

# --- AI CLIENTS ---
# Cloud: Gemini 2.5 Flash
cloud_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Local: Ollama (Gemma 3 1B)
local_client = LocalAI(base_url="http://localhost:11434/v1", api_key="ollama")