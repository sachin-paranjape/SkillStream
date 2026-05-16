import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
except ImportError:
    genai = None

try:
    from openai import OpenAI as LocalAI
except ImportError:
    LocalAI = None

# --- PATHS ---
DATA_PATH = "data/interactions.csv"
DB_PATH = "data/skillstream.db"
os.makedirs("data", exist_ok=True)

# --- AI CLIENTS ---
# Cloud: Gemini 2.5 Flash
cloud_client = None
if genai is not None:
    cloud_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Local: Ollama (Gemma 3 1B)
local_client = None
if LocalAI is not None:
    local_client = LocalAI(base_url="http://localhost:11434/v1", api_key="ollama")