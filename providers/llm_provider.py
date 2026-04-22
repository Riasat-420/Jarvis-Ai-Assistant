"""
Jarvis AI Assistant — LLM Provider Router
Manages connections to free LLM providers: Groq (primary) → Gemini (backup).
All providers are OpenAI-compatible, so the Agents SDK works with all of them.
"""

import sys
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

from config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    GROQ_FAST_MODEL,
    GEMINI_API_KEY,
)


def _validate_api_keys():
    """Check that at least one API key is configured."""
    if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_key_here":
        print("\n" + "=" * 60)
        print("⚠️  GROQ API KEY NOT CONFIGURED")
        print("=" * 60)
        print()
        print("Jarvis needs a FREE Groq API key to work.")
        print()
        print("Steps (takes 2 minutes, no credit card):")
        print("  1. Go to: https://console.groq.com")
        print("  2. Sign up with Google or email")
        print("  3. Go to: API Keys → Create API Key")
        print("  4. Copy the key (starts with 'gsk_')")
        print("  5. Paste it in your .env file:")
        print(f"     GROQ_API_KEY=gsk_your_actual_key")
        print()
        print("=" * 60)
        sys.exit(1)


def _create_groq_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client pointing to Groq's free API."""
    return AsyncOpenAI(
        base_url=GROQ_BASE_URL,
        api_key=GROQ_API_KEY,
    )


def _create_gemini_client() -> AsyncOpenAI | None:
    """Create an AsyncOpenAI client pointing to Gemini's API (optional backup)."""
    if not GEMINI_API_KEY:
        return None
    return AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=GEMINI_API_KEY,
    )


# ── Cached clients (created once) ─────────────────────────
_groq_client: AsyncOpenAI | None = None
_gemini_client: AsyncOpenAI | None = None


def _get_groq_client() -> AsyncOpenAI:
    """Get or create the Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _validate_api_keys()
        _groq_client = _create_groq_client()
    return _groq_client


def get_model() -> OpenAIChatCompletionsModel:
    """
    Get the primary LLM model for Jarvis agents.
    Uses Groq's Llama 3.3 70B — the most capable free model.
    """
    client = _get_groq_client()
    return OpenAIChatCompletionsModel(
        model=GROQ_MODEL,
        openai_client=client,
    )


def get_fast_model() -> OpenAIChatCompletionsModel:
    """
    Get a faster (but less capable) model for simple tasks.
    Uses Groq's Llama 3.1 8B — lightweight and instant.
    Good for: intent classification, simple Q&A.
    """
    client = _get_groq_client()
    return OpenAIChatCompletionsModel(
        model=GROQ_FAST_MODEL,
        openai_client=client,
    )
