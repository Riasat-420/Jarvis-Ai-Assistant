"""
Jarvis AI Assistant — Voice Speaker
Text-to-Speech using edge-tts with interrupt support.
Auto-detects language (English/Urdu) and switches voice accordingly.
Uses PowerShell for audio playback — supports instant stop via stop().
"""

import os
import re
import asyncio
import subprocess
import time
from pathlib import Path

from config import JARVIS_VOICE, TEMP_DIR

# ── Voice Configuration ────────────────────────────────────
URDU_VOICE = "ur-PK-AsadNeural"
ENGLISH_VOICE = JARVIS_VOICE


class VoiceSpeaker:
    """Handles text-to-speech with language detection and interrupt support."""

    def __init__(self, voice: str | None = None):
        self.voice = voice or ENGLISH_VOICE
        self.urdu_voice = URDU_VOICE
        self._process = None  # Active playback process (killable)
        self.was_interrupted = False  # Flag for interrupt detection
        self._cleanup_old_audio()

    def _cleanup_old_audio(self):
        """Remove old cached mp3 files to save space."""
        try:
            for file in TEMP_DIR.glob("jarvis_response_*.mp3"):
                try:
                    file.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    def _get_output_path(self) -> str:
        """Get a fresh output path for the new audio file."""
        import time
        return str(TEMP_DIR / f"jarvis_response_{int(time.time() * 1000)}.mp3")

    def _detect_language(self, text: str) -> str:
        """Detect if text is primarily Urdu or English."""
        if not text:
            return "en"
        urdu_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = sum(1 for c in text if c.isalpha() or '\u0600' <= c <= '\u06FF')
        if total_chars == 0:
            return "en"
        return "ur" if urdu_chars / total_chars > 0.3 else "en"

    async def _generate_speech(self, text: str) -> str:
        """Generate speech audio from text using edge-tts."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

        clean_text = self._clean_for_speech(text)
        if not clean_text.strip():
            return ""

        lang = self._detect_language(clean_text)
        voice = self.urdu_voice if lang == "ur" else self.voice

        output_path = self._get_output_path()
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(output_path)
        return output_path

    def _clean_for_speech(self, text: str) -> str:
        """Remove characters that don't translate well to speech."""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        text = re.sub(r'#{1,6}\s', '', text)
        text = re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
            r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            r'\U00002702-\U000027B0\U000024C2-\U0001F251'
            r'\U0000FE00-\U0000FE0F\U00002600-\U000026FF'
            r'✅❌⚠️🚫⏰💻🔍📁📂📄🌐✨🎤🔊💾🧠🎯]+',
            '', text
        )
        text = re.sub(r'```[\s\S]*?```', 'See the code on screen.', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > 300:
            sentences = text[:300].rsplit('.', 1)
            if len(sentences) > 1 and len(sentences[0]) > 50:
                text = sentences[0] + "."
            else:
                text = text[:300]

        return text

    def _start_playback(self, filepath: str):
        """Start audio playback as a background process (non-blocking, killable)."""
        ps_script = f'''
Add-Type -AssemblyName presentationCore
$mediaPlayer = New-Object System.Windows.Media.MediaPlayer
$mediaPlayer.Open([Uri]"{filepath}")
$mediaPlayer.Play()
Start-Sleep -Milliseconds 500
while ($mediaPlayer.NaturalDuration.HasTimeSpan -eq $false) {{
    Start-Sleep -Milliseconds 100
}}
$totalMs = $mediaPlayer.NaturalDuration.TimeSpan.TotalMilliseconds
Start-Sleep -Milliseconds ($totalMs - 400)
$mediaPlayer.Stop()
$mediaPlayer.Close()
'''
        try:
            self._process = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"  ⚠️  Audio start error: {e}")
            self._process = None

    def stop(self):
        """Immediately stop current audio playback."""
        if self._process and self._process.poll() is None:
            try:
                self._process.kill()
                self._process.wait(timeout=2)
            except Exception:
                pass
        self._process = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._process is not None and self._process.poll() is None

    def _wait_for_playback(self):
        """Block until playback finishes (used in executor)."""
        if self._process:
            self._process.wait()

    async def speak(self, text: str):
        """
        Generate speech and play it. Can be interrupted via stop().
        Sets self.was_interrupted if stopped early.
        """
        if not text or not text.strip():
            return

        self.was_interrupted = False

        try:
            audio_path = await self._generate_speech(text)
            if not audio_path:
                return

            abs_path = str(Path(audio_path).resolve())

            # Start playback (non-blocking)
            self._start_playback(abs_path)

            if self._process:
                # Wait for playback in a thread (so async loop stays free)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._wait_for_playback)

        except asyncio.CancelledError:
            self.stop()
            self.was_interrupted = True
        except Exception as e:
            print(f"  ⚠️  Speech error: {e}")

    def speak_sync(self, text: str):
        """Synchronous wrapper for speak()."""
        try:
            asyncio.run(self.speak(text))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.speak(text))
            loop.close()

    def set_voice(self, voice: str):
        """Change the TTS voice."""
        self.voice = voice
        print(f"  🔊 Voice changed to: {voice}")

    @staticmethod
    def list_voices():
        """Print available voice options."""
        voices = {
            "en-GB-RyanNeural": "British male (Classic Jarvis) ⭐",
            "en-US-GuyNeural": "American male, deep",
            "en-US-DavisNeural": "American male, calm & authoritative",
            "en-AU-WilliamNeural": "Australian male",
            "en-GB-SoniaNeural": "British female",
            "en-US-JennyNeural": "American female",
            "en-US-AriaNeural": "American female, expressive",
            "ur-PK-AsadNeural": "Urdu male (Pakistan) 🇵🇰",
            "ur-PK-UzmaNeural": "Urdu female (Pakistan) 🇵🇰",
        }
        print("\n🔊 Available Jarvis Voices:\n")
        for voice_id, description in voices.items():
            print(f"  {voice_id:30s} → {description}")
        print()
