"""
Jarvis AI Assistant — Centralized Configuration
Loads environment variables and defines all settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────
load_dotenv()

# ── Project Paths ──────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_DIR / "data"
TEMP_DIR = PROJECT_DIR / "temp"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# ── LLM Configuration ─────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

# ── Voice Configuration ───────────────────────────────────
JARVIS_VOICE = os.getenv("JARVIS_VOICE", "en-GB-RyanNeural")
WAKE_WORD = os.getenv("WAKE_WORD", "jarvis").lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Audio settings
SAMPLE_RATE = 16000       # 16kHz for Whisper
RECORD_CHANNELS = 1       # Mono
SILENCE_THRESHOLD = 0.01  # Energy threshold for silence detection
SILENCE_DURATION = 1.5    # Seconds of silence before stopping
MAX_RECORD_DURATION = 30  # Max recording time in seconds
MIN_RECORD_DURATION = 1   # Min recording time in seconds

# ── Safety Configuration ──────────────────────────────────
# Commands that are ALWAYS blocked (case-insensitive check)
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf *",
    "del /s /q c:",
    "format c:",
    "format d:",
    "shutdown",
    "restart",
    ":(){:|:&};:",      # Fork bomb
    "mkfs",
    "dd if=",
    "> /dev/sda",
    "chmod -R 777 /",
    "wget | sh",
    "curl | sh",
    "powershell -enc",  # Encoded commands (potential malware)
    "reg delete",
    "bcdedit",
]

# Max execution time for commands (seconds)
MAX_COMMAND_TIMEOUT = 30

# Max output length from commands (characters)
MAX_OUTPUT_LENGTH = 3000

# Directories the file agent can access (expand as needed)
ALLOWED_DIRECTORIES = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    PROJECT_DIR,
]

# ── Jarvis Personality ─────────────────────────────────────
JARVIS_GREETING = "Jarvis online. How can I assist you, sir?"
JARVIS_ACTIVATION_SOUND = "✨"  # Printed when wake word detected

# ── Database ───────────────────────────────────────────────
DB_PATH = DATA_DIR / "jarvis_memory.db"
