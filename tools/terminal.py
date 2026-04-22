"""
Jarvis AI Assistant — Terminal Tool
Safe subprocess execution with command blocklisting and timeout protection.
"""

import subprocess
import shlex
from agents import function_tool
from config import BLOCKED_COMMANDS, MAX_COMMAND_TIMEOUT, MAX_OUTPUT_LENGTH


def _is_command_blocked(command: str) -> str | None:
    """Check if a command is blocked. Returns reason if blocked, None if safe."""
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return f"🚫 Command blocked for safety: contains '{blocked}'"
    return None


@function_tool(strict_mode=False)
def run_terminal_command(command: str) -> str:
    """
    Execute a terminal/shell command on the local system and return its output.
    Use this for running scripts, checking system status, package management, etc.

    Args:
        command: The command to execute (e.g., "dir", "python --version", "npm install").

    Returns:
        The command's stdout and stderr output, or an error message.
    """
    # Safety check
    blocked_reason = _is_command_blocked(command)
    if blocked_reason:
        return blocked_reason

    try:
        # Run the command using PowerShell on Windows for best compatibility
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=MAX_COMMAND_TIMEOUT,
            cwd=None,  # Uses current directory
        )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout.strip())
        if result.stderr:
            output_parts.append(f"[STDERR]: {result.stderr.strip()}")

        output = "\n".join(output_parts) if output_parts else "(no output)"

        # Add return code info
        if result.returncode != 0:
            output = f"[Exit code: {result.returncode}]\n{output}"

        # Truncate if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n... (truncated, {len(output)} total chars)"

        return output

    except subprocess.TimeoutExpired:
        return f"⏰ Command timed out after {MAX_COMMAND_TIMEOUT} seconds."
    except FileNotFoundError:
        return "❌ PowerShell not found. Cannot execute commands."
    except Exception as e:
        return f"❌ Error executing command: {type(e).__name__}: {str(e)}"


@function_tool(strict_mode=False)
def run_python_code(code: str) -> str:
    """
    Execute a Python code snippet and return the output.
    Useful for quick calculations, data processing, or testing code.

    Args:
        code: The Python code to execute.

    Returns:
        The code's stdout output, or an error message.
    """
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=MAX_COMMAND_TIMEOUT,
        )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout.strip())
        if result.stderr:
            output_parts.append(f"[Error]: {result.stderr.strip()}")

        output = "\n".join(output_parts) if output_parts else "(no output)"

        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... (truncated)"

        return output

    except subprocess.TimeoutExpired:
        return f"⏰ Code execution timed out after {MAX_COMMAND_TIMEOUT} seconds."
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {str(e)}"
