"""
config.py - Central Configuration Ledger for Maggie AI
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Identity & Wake Word
ASSISTANT_NAME = "Maggie"
WAKE_WORD = "maggie"

# Voice & STT Engine Settings
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en-US")
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AvaNeural")
TTS_SPEED = os.getenv("TTS_SPEED", "+0%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")

VOICE_POOL = [
    "en-US-AvaNeural",
    "en-US-JennyNeural",
    "en-US-EmmaNeural",
    "en-GB-SoniaNeural",
    "en-AU-NatashaNeural",
]

# API Keys & Local Models
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Directories & Storage Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
MEMORY_DIR = os.path.join(DATA_DIR, "memory")

for path in [DATA_DIR, LOG_DIR, MEMORY_DIR]:
    os.makedirs(path, exist_ok=True)

DB_PATH = os.path.join(MEMORY_DIR, "maggie_memory.db")
AUDIO_OUT_PATH = os.path.join(DATA_DIR, "_reply.mp3")
FILE_SEARCH_ROOT = os.path.expanduser(os.getenv("FILE_SEARCH_ROOT", "~"))

# Security & Safeguards
CONFIRMATION_REQUIRED_COMMANDS = ["shutdown", "restart", "delete_file", "sudo"]
