"""
Jarvis AI Assistant — Voice Listener
Microphone capture → Whisper Speech-to-Text.
Uses faster-whisper for efficient local transcription.
"""

import io
import wave
import tempfile
import numpy as np
from pathlib import Path

from config import (
    SAMPLE_RATE,
    RECORD_CHANNELS,
    WHISPER_MODEL,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_DURATION,
    MIN_RECORD_DURATION,
    TEMP_DIR,
)


class VoiceListener:
    """Handles microphone recording and speech-to-text transcription."""

    def __init__(self):
        self._model = None
        self._sd = None

    def _ensure_imports(self):
        """Lazy-import heavy dependencies."""
        if self._sd is None:
            try:
                import sounddevice as sd
                self._sd = sd
            except ImportError:
                raise ImportError(
                    "sounddevice not installed. Run: pip install sounddevice"
                )
            except OSError as e:
                raise OSError(
                    f"Audio device error: {e}\n"
                    "Make sure you have a microphone connected."
                )

    def _ensure_model(self):
        """Lazy-load the Whisper model (only on first use)."""
        if self._model is None:
            try:
                import os
                import warnings

                # Suppress noisy HuggingFace warnings on Windows
                os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
                warnings.filterwarnings("ignore", message=".*huggingface_hub.*")
                warnings.filterwarnings("ignore", message=".*unauthenticated.*")

                from faster_whisper import WhisperModel
                print(f"  Loading Whisper ({WHISPER_MODEL}) model... ", end="", flush=True)
                self._model = WhisperModel(
                    WHISPER_MODEL,
                    device="cpu",
                    compute_type="int8",
                )
                print("✅")
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. Run: pip install faster-whisper"
                )

    def record_fixed(self, duration: float = 5.0) -> np.ndarray:
        """
        Record audio from microphone for a fixed duration.

        Args:
            duration: Recording duration in seconds.

        Returns:
            Numpy array of recorded audio (float32, mono, 16kHz).
        """
        self._ensure_imports()
        sd = self._sd

        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=RECORD_CHANNELS,
            dtype="float32",
        )
        sd.wait()
        return audio.flatten()

    def record_until_silence(self) -> np.ndarray:
        """
        Record audio from microphone until silence is detected.
        Uses energy-based Voice Activity Detection (VAD).

        Returns:
            Numpy array of recorded audio.
        """
        self._ensure_imports()
        sd = self._sd

        chunk_duration = 0.5  # Check every 500ms
        chunk_samples = int(chunk_duration * SAMPLE_RATE)
        max_chunks = int(MAX_RECORD_DURATION / chunk_duration)
        silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)

        all_audio = []
        silence_count = 0
        total_chunks = 0
        has_speech = False

        # Open a stream for continuous recording
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=RECORD_CHANNELS,
            dtype="float32",
        ) as stream:
            while total_chunks < max_chunks:
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                all_audio.append(chunk)
                total_chunks += 1

                # Calculate RMS energy of this chunk
                energy = np.sqrt(np.mean(chunk ** 2))

                if energy > SILENCE_THRESHOLD:
                    has_speech = True
                    silence_count = 0
                else:
                    silence_count += 1

                # Stop if we had speech and now silence for long enough
                elapsed = total_chunks * chunk_duration
                if has_speech and silence_count >= silence_chunks_needed and elapsed >= MIN_RECORD_DURATION:
                    break

        return np.concatenate(all_audio)

    def _audio_to_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert a numpy audio array to WAV bytes for Whisper."""
        # Convert float32 [-1, 1] to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(RECORD_CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    def _save_temp_wav(self, audio: np.ndarray) -> str:
        """Save audio to a temporary WAV file and return the path."""
        wav_path = str(TEMP_DIR / "recording.wav")
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(RECORD_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        return wav_path

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio: Numpy array of audio data.

        Returns:
            Transcribed text string.
        """
        self._ensure_model()

        # Save to temp WAV (faster-whisper works best with files)
        wav_path = self._save_temp_wav(audio)

        segments, info = self._model.transcribe(
            wav_path,
            language="en",
            beam_size=5,
            vad_filter=True,  # Filter out non-speech
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text

    def listen(self, mode: str = "auto") -> str:
        """
        Record from microphone and transcribe to text.

        Args:
            mode: "auto" (stop on silence), "fixed" (5 seconds).

        Returns:
            Transcribed text.
        """
        if mode == "fixed":
            audio = self.record_fixed(5.0)
        else:
            audio = self.record_until_silence()

        # Skip if too quiet (no real speech detected)
        energy = np.sqrt(np.mean(audio ** 2))
        if energy < SILENCE_THRESHOLD * 0.5:
            return ""

        text = self.transcribe(audio)
        return text

    def listen_with_timeout(self, timeout: float = 10.0) -> str:
        """
        Listen for speech with a timeout. Used for follow-up conversation mode.
        Waits up to `timeout` seconds for speech to begin. If speech is detected,
        continues recording until silence, then transcribes. If no speech is
        detected within the timeout, returns empty string.

        Args:
            timeout: Max seconds to wait for speech to begin.

        Returns:
            Transcribed text, or "" if no speech was detected.
        """
        self._ensure_imports()
        sd = self._sd

        chunk_duration = 0.5
        chunk_samples = int(chunk_duration * SAMPLE_RATE)
        timeout_chunks = int(timeout / chunk_duration)
        max_total_chunks = int(MAX_RECORD_DURATION / chunk_duration)
        silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)

        all_audio = []
        silence_count = 0
        total_chunks = 0
        has_speech = False
        waiting_chunks = 0

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=RECORD_CHANNELS,
            dtype="float32",
        ) as stream:
            while total_chunks < max_total_chunks:
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                total_chunks += 1

                energy = np.sqrt(np.mean(chunk ** 2))

                if not has_speech:
                    # Still waiting for speech to begin
                    waiting_chunks += 1
                    if energy > SILENCE_THRESHOLD:
                        has_speech = True
                        all_audio.append(chunk)
                        silence_count = 0
                    elif waiting_chunks >= timeout_chunks:
                        # Timeout — no speech detected
                        return ""
                else:
                    # Recording speech
                    all_audio.append(chunk)
                    if energy > SILENCE_THRESHOLD:
                        silence_count = 0
                    else:
                        silence_count += 1

                    elapsed = len(all_audio) * chunk_duration
                    if silence_count >= silence_chunks_needed and elapsed >= MIN_RECORD_DURATION:
                        break

        if not all_audio:
            return ""

        audio = np.concatenate(all_audio)
        energy = np.sqrt(np.mean(audio ** 2))
        if energy < SILENCE_THRESHOLD * 0.5:
            return ""

        return self.transcribe(audio)

