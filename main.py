"""
╔══════════════════════════════════════════════════════════════╗
║                    🧠 JARVIS AI ASSISTANT                     ║
║                                                               ║
║  Multi-agent AI system with voice interface.                  ║
║  Powered by Groq (free) + OpenAI Agents SDK.                 ║
║                                                               ║
║  Usage:                                                       ║
║    python main.py              Voice mode (primary)           ║
║    python main.py --text       Text/CLI mode                  ║
║    python main.py --no-wake    Voice without wake word        ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import argparse
import asyncio

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from colorama import init as colorama_init, Fore, Style
from jarvis_agents.orchestrator import create_orchestrator
from memory.store import MemoryStore
from config import JARVIS_GREETING


# ── Initialize ─────────────────────────────────────────────
colorama_init()

# Color shortcuts
C = Fore.CYAN
G = Fore.GREEN
Y = Fore.YELLOW
R = Fore.RED
M = Fore.MAGENTA
W = Fore.WHITE
DIM = Style.DIM
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT


def print_banner():
    """Print the Jarvis startup banner."""
    banner = f"""
{C}{BRIGHT}╔══════════════════════════════════════════╗
║                                          ║
║   ░░█ ▄▀█ █▀█ █░█ █ █▀   {Y}v1.0{C}           ║
║   █▄█ █▀█ █▀▄ ▀▄▀ █ ▄█               ║
║                                          ║
║   {W}Multi-Agent AI Assistant{C}               ║
║   {DIM}Powered by Groq + Agents SDK{C}{BRIGHT}          ║
║                                          ║
╚══════════════════════════════════════════╝{RESET}
"""
    print(banner)


def print_status(text: str, color=G):
    """Print a status message."""
    print(f"  {color}▸{RESET} {text}")


# ══════════════════════════════════════════════════════════════
# TEXT MODE
# ══════════════════════════════════════════════════════════════

async def run_text_mode():
    """Run Jarvis in CLI text mode."""
    print_banner()
    print_status("Initializing agents...", Y)

    orchestrator = create_orchestrator()
    memory = MemoryStore()

    print_status(f"Text mode active. Type your message below.", G)
    print_status(f"Type 'quit' to exit, 'history' for recent messages.\n", DIM)

    # Greeting
    print(f"  {C}{BRIGHT}Jarvis:{RESET} {JARVIS_GREETING}\n")

    while True:
        try:
            # Get user input
            user_input = input(f"  {G}You:{RESET} ").strip()

            if not user_input:
                continue

            # Special commands
            if user_input.lower() in ("quit", "exit", "bye", "goodbye"):
                print(f"\n  {C}Jarvis:{RESET} Goodbye, sir. Systems shutting down.\n")
                break

            if user_input.lower() == "history":
                messages = memory.get_recent_messages(10)
                if messages:
                    print(f"\n  {Y}Recent conversation:{RESET}")
                    for msg in messages:
                        role = "You" if msg["role"] == "user" else "Jarvis"
                        agent_tag = f" [{msg['agent']}]" if msg.get("agent") else ""
                        content_preview = msg["content"][:100]
                        print(f"    {DIM}{role}{agent_tag}:{RESET} {content_preview}")
                    print()
                else:
                    print(f"  {DIM}No conversation history yet.{RESET}\n")
                continue

            if user_input.lower() == "clear":
                memory.clear_history()
                print(f"  {Y}History cleared.{RESET}\n")
                continue

            # Save user message
            memory.save_message("user", user_input)

            # Process with orchestrator
            print(f"\n  {C}{BRIGHT}Jarvis:{RESET} ", end="", flush=True)

            try:
                history = memory.get_recent_messages(6)
                response, agent_name = await orchestrator.process(user_input, history=history)

                # Print response
                print(f"{response}\n")

                # Show which agent handled it
                if agent_name and agent_name != "Jarvis":
                    print(f"  {DIM}[Handled by: {agent_name}]{RESET}\n")

                # Save assistant response
                memory.save_message("assistant", response, agent=agent_name)

            except Exception as e:
                error_msg = str(e)
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    print(f"{Y}Rate limit reached. Please wait a moment and try again.{RESET}\n")
                elif "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                    print(f"{R}API key issue. Check your .env file.{RESET}\n")
                else:
                    print(f"{R}Error: {error_msg}{RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n  {C}Jarvis:{RESET} Interrupted. Goodbye, sir.\n")
            break
        except EOFError:
            break


# ══════════════════════════════════════════════════════════════
# VOICE MODE
# ══════════════════════════════════════════════════════════════

def _wait_for_interrupt_key(speaker):
    """
    Block until the user presses Enter to interrupt Jarvis.
    Runs in a background thread alongside audio playback.
    """
    import msvcrt
    while speaker.is_playing():
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key in (b'\r', b'\n', b' '):
                speaker.stop()
                speaker.was_interrupted = True
                return True
        import time
        time.sleep(0.05)
    return False


async def run_voice_mode(use_wake_word: bool = True):
    """Run Jarvis in voice mode with continuous conversation and interrupt support."""
    print_banner()
    print_status("Initializing voice system...", Y)

    # Import voice components
    from voice.listener import VoiceListener
    from voice.speaker import VoiceSpeaker
    from voice.wake_word import WakeWordDetector

    # Initialize components
    listener = VoiceListener()
    speaker = VoiceSpeaker()
    memory = MemoryStore()

    print_status("Loading speech-to-text model...", Y)
    listener._ensure_imports()
    listener._ensure_model()

    print_status("Initializing AI agents...", Y)
    orchestrator = create_orchestrator()

    print_status(f"Voice: {speaker.voice}", G)

    if use_wake_word:
        detector = WakeWordDetector(listener)
        print_status(f"Wake word: 'Jarvis'", G)
        print_status("Say 'Jarvis' followed by your command.", G)
        print_status("Press Enter to interrupt Jarvis while speaking.", G)
        print_status(f"Mic stays active for follow-ups after each reply.\n", G)
    else:
        print_status("Wake word disabled. Press Enter to speak.\n", G)

    # Speak greeting
    print(f"  {C}{BRIGHT}Jarvis:{RESET} {JARVIS_GREETING}")
    await speaker.speak(JARVIS_GREETING)
    print()

    # ── Conversation state ─────────────────────────────────
    FOLLOW_UP_TIMEOUT = 10.0
    in_conversation = False

    while True:
        try:
            # ── Step 1: Get user input ─────────────────────
            user_text = None

            if in_conversation:
                # FOLLOW-UP MODE: Mic stays active, no wake word needed
                print(f"  {C}🎤 Listening...{RESET} {DIM}(say something or stay silent to end){RESET}", end="\r")
                user_text = listener.listen_with_timeout(timeout=FOLLOW_UP_TIMEOUT)

                if not user_text or not user_text.strip():
                    in_conversation = False
                    print(f"  {DIM}💤 Conversation paused. Say 'Jarvis' to resume.{RESET}          ")
                    continue

            elif use_wake_word:
                # WAKE WORD MODE: Wait for "Jarvis"
                print(f"  {DIM}🎤 Listening for 'Jarvis'...{RESET}", end="\r")

                def on_wake():
                    print(f"  {G}{BRIGHT}✨ Activated! Listening...{RESET}    ")

                user_text = detector.wait_for_activation(callback=on_wake)
                in_conversation = True

            else:
                # MANUAL MODE
                input(f"  {DIM}Press Enter to speak...{RESET}")
                print(f"  {G}🎤 Listening...{RESET}")
                user_text = listener.listen(mode="auto")
                in_conversation = True

            if not user_text or not user_text.strip():
                continue

            # ── Step 2: Show what was heard ────────────────
            print(f"  {G}You:{RESET} {user_text}")
            memory.save_message("user", user_text)

            # Special voice commands
            if user_text.lower().strip() in ("stop", "quit", "exit", "goodbye", "shut down", "go to sleep"):
                farewell = "Shutting down. Goodbye, sir."
                print(f"  {C}Jarvis:{RESET} {farewell}")
                await speaker.speak(farewell)
                break

            if user_text.lower().strip() in ("never mind", "cancel", "nothing", "forget it"):
                print(f"  {C}Jarvis:{RESET} Standing by, sir.")
                await speaker.speak("Standing by, sir.")
                in_conversation = False
                continue

            # ── Step 3: Process with orchestrator ──────────
            print(f"  {C}{BRIGHT}Jarvis:{RESET} ", end="", flush=True)

            try:
                history = memory.get_recent_messages(6)
                response, agent_name = await orchestrator.process(user_text, history=history)

                print(f"{response}")
                if agent_name and agent_name != "Jarvis":
                    print(f"  {DIM}[{agent_name}]{RESET}")

                memory.save_message("assistant", response, agent=agent_name)

                # ── Step 4: Speak with interrupt support ───
                speaker.was_interrupted = False

                # Start speaking (background subprocess)
                speak_task = asyncio.create_task(speaker.speak(response))

                # Run keyboard monitor concurrently
                loop = asyncio.get_event_loop()
                interrupt_future = loop.run_in_executor(None, _wait_for_interrupt_key, speaker)

                # Wait for EITHER: speech finishes OR Enter pressed
                done, pending = await asyncio.wait(
                    [speak_task, asyncio.ensure_future(interrupt_future)],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                # Handle interrupt — listen for new command immediately
                if speaker.was_interrupted:
                    print(f"\n  {Y}⚡ Interrupted! Listening...{RESET}")
                    new_text = listener.listen(mode="auto")
                    if new_text and new_text.strip():
                        print(f"  {G}You:{RESET} {new_text}")
                        memory.save_message("user", new_text)
                        print(f"  {C}{BRIGHT}Jarvis:{RESET} ", end="", flush=True)
                        history = memory.get_recent_messages(6)
                        response, agent_name = await orchestrator.process(new_text, history=history)
                        print(f"{response}")
                        if agent_name and agent_name != "Jarvis":
                            print(f"  {DIM}[{agent_name}]{RESET}")
                        await speaker.speak(response)
                        memory.save_message("assistant", response, agent=agent_name)

                in_conversation = True

            except Exception as e:
                error_msg = str(e)
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    msg = "Rate limit reached. Please wait a moment."
                elif "api_key" in error_msg.lower():
                    msg = "API key issue. Please check your configuration."
                else:
                    msg = f"I encountered an error: {error_msg[:100]}"

                print(f"{R}{msg}{RESET}")
                await speaker.speak(msg)
                in_conversation = True

            print()  # Blank line between interactions

        except KeyboardInterrupt:
            print(f"\n\n  {C}Jarvis:{RESET} Interrupted. Goodbye, sir.\n")
            break
        except Exception as e:
            print(f"\n  {R}System error: {e}{RESET}")
            print(f"  {DIM}Recovering...{RESET}\n")
            in_conversation = False
            continue


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main():
    """Parse arguments and run Jarvis in the selected mode."""
    parser = argparse.ArgumentParser(
        description="Jarvis AI Assistant — Multi-agent system with voice interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Start in voice mode (say 'Jarvis' to activate)
  python main.py --text       Start in text/CLI mode
  python main.py --no-wake    Voice mode without wake word (press Enter to speak)
        """
    )

    parser.add_argument(
        "--text", "-t",
        action="store_true",
        help="Run in text/CLI mode instead of voice mode"
    )
    parser.add_argument(
        "--no-wake", "-n",
        action="store_true",
        help="Voice mode without wake word (press Enter to speak)"
    )

    args = parser.parse_args()

    try:
        if args.text:
            asyncio.run(run_text_mode())
        else:
            asyncio.run(run_voice_mode(use_wake_word=not args.no_wake))
    except KeyboardInterrupt:
        print(f"\n{C}Jarvis shutting down.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
