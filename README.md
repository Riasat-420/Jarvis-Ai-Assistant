# Jarvis AI Assistant 🤖

**Jarvis** is a powerful, multi-agent AI assistant designed for Windows. Inspired by Iron Man's JARVIS, it allows for seamless voice interactions, continuous conversation, screen awareness, and specialized agent routing using the free Groq API.

## ✨ Key Features
- **Continuous Voice Interaction:** "Buttery smooth" conversation flow. Say "Jarvis" once, and the microphone stays active for the remainder of your conversation.
- **Bilingual Support (English & Urdu):** Automatically detects if you're speaking Urdu or English and dynamically switches Text-to-Speech (TTS) voices (e.g., `en-GB-RyanNeural` to `ur-PK-AsadNeural`).
- **Interruptible Speech:** Press `Enter` or `Space` at any time while Jarvis is speaking to immediately cut him off and give a new command.
- **Screen Awareness:** Uses Windows system APIs and Groq's Vision models to capture your screen, list active windows, and intelligently describe what you are looking at upon request.
- **Multi-Agent Orchestration:** Features a Python-based intelligent router (`orchestrator.py`) that classifies your request and delegates it to specialist agents (File Manager, Dev Agent, Debug Agent, or SEO Agent).
- **System Interactions:** Jarvis can browse local directories, read files, open/close local applications (like Chrome or VS Code), and fetch system info.

## 🛠️ Architecture
The assistant uses the `openai-agents` Python SDK mapped to the **Groq** API (Llama 3.3 70B & Llama-4 Vision) for unparalleled speed at zero cost.

- **`main.py`:** Initiates the voice mode loop, listens for the wake word, and handles interrupt logic.
- **`jarvis_agents/orchestrator.py`:** A lightweight intent classifier that routes queries so the optimal agent handles the task.
- **`tools/screen_tools.py`:** Dependency-free (PowerShell-based) screenshot + window scanning toolkit that feeds image data into Groq Vision.
- **`voice/speaker.py`:** `edge-tts` backed speech synthesis. It uses non-blocking Windows MediaPlayer processes, which allows it to be instantly killed when an interrupt key is pressed.

## 🚀 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Riasat-420/Jarvis-Ai-Assistant.git
   cd Jarvis-Ai-Assistant
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: `edge-tts` and `faster-whisper` are the core audio engines).*

3. **Configure the Environment:**
   Create a `.env` file in the root directory and add your free [Groq API Key](https://console.groq.com/keys):
   ```env
   GROQ_API_KEY=gsk_your_key_here
   GROQ_BASE_URL=https://api.groq.com/openai/v1
   GROQ_MODEL=llama-3.3-70b-versatile
   GROQ_FAST_MODEL=llama-3.1-8b-instant
   ```

4. **Run Jarvis:**
   ```bash
   python main.py
   ```
   Wait for the voice engine to initialize, say "Jarvis" to wake him up, and begin speaking!

## 🔧 Useful Commands
- `"Jarvis, open Chrome"`
- `"Close the web browser"`
- `"What am I looking at right now?"` (Triggers screenshot + visual analysis)
- `"What apps do I have running?"`
- `"Read me the contents of requirements.txt"`
- `(Press Enter)` completely cuts off his speech so you can interrupt him.

## 📝 License
This project is for educational and personal use. Relies on free third-party libraries: `faster-whisper` and `edge-tts`.
