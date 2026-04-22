"""
Jarvis AI Assistant — Screen Awareness Tools
Active window detection, window listing, and screenshot + vision analysis.
Uses Windows APIs and PowerShell — no extra image libraries needed.
"""

import os
import ctypes
import ctypes.wintypes
import subprocess
import base64
from pathlib import Path
from agents import function_tool
from config import GROQ_API_KEY, GROQ_BASE_URL, TEMP_DIR


# ── Raw helper functions (used internally, not as tools) ────
def _get_active_window_raw() -> str:
    """Get active window title without the tool wrapper."""
    try:
        user32 = ctypes.windll.user32
        h_wnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(h_wnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h_wnd, buf, length + 1)
        return buf.value or "Unknown window"
    except Exception:
        return "Could not detect active window"


def _get_all_windows_raw() -> str:
    """List all windows without the tool wrapper."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | "
             "Select-Object ProcessName, MainWindowTitle | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "No windows found"
    except Exception:
        return "Could not list windows"


# ══════════════════════════════════════════════════════════════
# TOOL 1: Get Active Window
# ══════════════════════════════════════════════════════════════

@function_tool(strict_mode=False)
def get_active_window(detail: str) -> str:
    """
    Get information about the currently active/focused window on the user's screen.
    Use this to understand what the user is currently looking at or working on.

    Args:
        detail: Level of detail. "full" for title + process, "title" for just the window title.

    Returns:
        The active window's title, application name, and process info.
    """
    try:
        # Get foreground window handle
        user32 = ctypes.windll.user32
        h_wnd = user32.GetForegroundWindow()

        # Get window title
        length = user32.GetWindowTextLengthW(h_wnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h_wnd, buf, length + 1)
        title = buf.value

        if not title:
            return "No active window detected (desktop may be focused)."

        if detail == "title":
            return f"Active window: {title}"

        # Get the process name for the window
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(h_wnd, ctypes.byref(pid))

        process_info = ""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process -Id {pid.value} -ErrorAction SilentlyContinue | "
                 f"Select-Object ProcessName, Path | Format-List"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip():
                process_info = result.stdout.strip()
        except Exception:
            pass

        lines = [f"🖥️  Active Window Information:"]
        lines.append(f"  Title: {title}")
        if process_info:
            lines.append(f"  {process_info}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error getting active window: {str(e)}"


# ══════════════════════════════════════════════════════════════
# TOOL 2: List All Open Windows
# ══════════════════════════════════════════════════════════════

@function_tool(strict_mode=False)
def get_all_windows(filter_text: str) -> str:
    """
    List all currently open windows/applications on the user's screen.
    Use this to see what programs the user has running.

    Args:
        filter_text: Optional filter to search for specific windows (e.g., "chrome", "code"). Pass empty string "" for all.

    Returns:
        A formatted list of all open windows with their application names.
    """
    try:
        # Use PowerShell to get all windows with titles
        ps_cmd = (
            "Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | "
            "Select-Object ProcessName, MainWindowTitle, Id | "
            "Sort-Object ProcessName | Format-Table -AutoSize -Wrap"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
        )

        output = result.stdout.strip()
        if not output:
            return "No windows with visible titles found."

        if filter_text:
            # Filter the results
            lines = output.split("\n")
            header = lines[:3]  # Keep table header
            filtered = [l for l in lines[3:] if filter_text.lower() in l.lower()]
            if filtered:
                output = "\n".join(header + filtered)
            else:
                return f"No windows matching '{filter_text}' found."

        return f"🖥️  Open Windows:\n{output}"

    except Exception as e:
        return f"❌ Error listing windows: {str(e)}"


# ══════════════════════════════════════════════════════════════
# TOOL 3: Screenshot + Vision Description
# ══════════════════════════════════════════════════════════════

def _capture_screenshot_powershell() -> str | None:
    """
    Capture a screenshot using PowerShell (no Python image libs needed).
    Saves as compressed JPEG to temp directory.
    Returns the file path, or None on failure.
    """
    screenshot_path = str(TEMP_DIR / "screenshot.jpg")

    ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [Drawing.Point]::Empty, $screen.Size)

# Save as JPEG with 50% quality for smaller file size
$encoder = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object {{ $_.MimeType -eq 'image/jpeg' }}
$params = New-Object Drawing.Imaging.EncoderParameters(1)
$params.Param[0] = New-Object Drawing.Imaging.EncoderParameter([Drawing.Imaging.Encoder]::Quality, [long]50)
$bitmap.Save("{screenshot_path}", $encoder, $params)

$graphics.Dispose()
$bitmap.Dispose()
Write-Output "OK"
'''

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and Path(screenshot_path).exists():
            return screenshot_path
        return None
    except Exception:
        return None


def _describe_image_with_vision(image_b64: str, question: str) -> str:
    """Send a base64 image to Groq's vision model and get a description."""
    from openai import OpenAI

    client = OpenAI(
        base_url=GROQ_BASE_URL,
        api_key=GROQ_API_KEY,
    )

    try:
        response = client.chat.completions.create(
            model="llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"You are Jarvis, an AI assistant. The user is asking about what's on their screen. "
                            f"Describe what you see concisely and helpfully. "
                            f"User's question: {question}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    },
                ],
            }],
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Vision analysis failed: {str(e)[:150]}"


@function_tool(strict_mode=False)
def describe_screen(question: str) -> str:
    """
    Take a screenshot of the user's screen and describe what is visible.
    Use this when the user asks what's on their screen, what they're looking at,
    or needs help with something visible on their display.

    Args:
        question: The user's question about their screen (e.g., "What am I looking at?",
                  "What error is showing?", "Read the text on screen").

    Returns:
        A description of what's visible on the user's screen.
    """
    # Step 1: Capture screenshot
    screenshot_path = _capture_screenshot_powershell()
    if not screenshot_path:
        # Fallback: just return window info
        active = _get_active_window_raw()
        windows = _get_all_windows_raw()
        return f"Could not capture screenshot. Here's what I can see:\n\n{active}\n\n{windows}"

    # Step 2: Read and encode the image
    try:
        with open(screenshot_path, "rb") as f:
            image_data = f.read()

        # Check file size (Groq limit ~20MB for requests, but let's be conservative)
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > 4:
            return (
                "Screenshot is too large for vision analysis. "
                "I can still tell you that " + _get_active_window_raw()
            )

        image_b64 = base64.b64encode(image_data).decode("utf-8")

    except Exception as e:
        return f"Error reading screenshot: {str(e)}"

    # Step 3: Send to vision model
    description = _describe_image_with_vision(image_b64, question)

    # Clean up
    try:
        os.unlink(screenshot_path)
    except Exception:
        pass

    return description
