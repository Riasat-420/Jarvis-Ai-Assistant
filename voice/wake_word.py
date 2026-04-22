"""
Jarvis AI Assistant — Wake Word Detection
Listens continuously for "Jarvis" to activate full listening mode.
Uses short Whisper transcriptions for keyword detection.
"""

import numpy as np
from config import WAKE_WORD, SAMPLE_RATE, SILENCE_THRESHOLD


class WakeWordDetector:
    """Detects the wake word 'Jarvis' from continuous microphone input."""

    def __init__(self, listener):
        """
        Args:
            listener: A VoiceListener instance for recording and transcription.
        """
        self.listener = listener
        self.wake_word = WAKE_WORD
        self._sd = None

    def _ensure_imports(self):
        """Lazy-import sounddevice."""
        if self._sd is None:
            import sounddevice as sd
            self._sd = sd

    def listen_for_wake_word(self) -> bool:
        """
        Record a short audio clip and check if it contains the wake word.

        Returns:
            True if wake word was detected, False otherwise.
        """
        self._ensure_imports()
        sd = self._sd

        # Record 2-second chunk
        duration = 2.0
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = audio.flatten()

        # Skip if too quiet
        energy = np.sqrt(np.mean(audio ** 2))
        if energy < SILENCE_THRESHOLD * 0.3:
            return False

        # Transcribe the short clip
        try:
            text = self.listener.transcribe(audio)
            text_lower = text.lower().strip()

            # Check for wake word
            if self.wake_word in text_lower:
                return True

            # Also check common misheard variants
            variants = ["jarvis", "travis", "jervis", "jarvas", "javis"]
            for variant in variants:
                if variant in text_lower:
                    return True

        except Exception:
            pass

        return False

    def wait_for_activation(self, callback=None) -> str:
        """
        Block until the wake word is detected, then record the full command.

        Args:
            callback: Optional function called when wake word is detected.

        Returns:
            The transcribed user command (after the wake word).
        """
        while True:
            if self.listen_for_wake_word():
                # Wake word detected!
                if callback:
                    callback()

                # Now listen for the full command
                text = self.listener.listen(mode="auto")
                if text.strip():
                    # Remove the wake word from the beginning if present
                    text_clean = text.strip()
                    for prefix in ["jarvis", "hey jarvis", "ok jarvis", "jarvis,"]:
                        if text_clean.lower().startswith(prefix):
                            text_clean = text_clean[len(prefix):].strip()
                            if text_clean.startswith(",") or text_clean.startswith("."):
                                text_clean = text_clean[1:].strip()
                            break

                    if text_clean:
                        return text_clean

                # If no command after wake word, keep listening
