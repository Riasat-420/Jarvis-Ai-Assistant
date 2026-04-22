"""
Jarvis AI Assistant — System Tools
App launcher, URL opener, system info, and process management.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from agents import function_tool


@function_tool(strict_mode=False)
def open_application(app_name: str) -> str:
    """
    Open a local application by name. Supports common apps like
    VS Code, Chrome, Notepad, File Explorer, etc.

    Args:
        app_name: Name of the application to open (e.g., "chrome", "code", "notepad").

    Returns:
        Success or error message.
    """
    # Map of common app names to their Windows executables/commands
    app_map = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "browser": "start chrome",
        "firefox": "start firefox",
        "edge": "start msedge",
        "notepad": "notepad",
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "explorer": "explorer",
        "file explorer": "explorer",
        "files": "explorer",
        "cmd": "start cmd",
        "command prompt": "start cmd",
        "terminal": "start wt",  # Windows Terminal
        "powershell": "start powershell",
        "calculator": "calc",
        "calc": "calc",
        "paint": "mspaint",
        "word": "start winword",
        "excel": "start excel",
        "task manager": "taskmgr",
        "settings": "start ms-settings:",
        "control panel": "control",
    }

    app_lower = app_name.lower().strip()
    command = app_map.get(app_lower)

    if not command:
        # Try running the name directly as a command
        command = f"start {app_name}"

    try:
        subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"✅ Opened: {app_name}"
    except Exception as e:
        return f"❌ Could not open '{app_name}': {str(e)}"


@function_tool(strict_mode=False)
def open_url(url: str) -> str:
    """
    Open a URL in the default web browser.

    Args:
        url: The URL to open (e.g., "https://google.com").

    Returns:
        Success or error message.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        import webbrowser
        webbrowser.open(url)
        return f"✅ Opened in browser: {url}"
    except Exception as e:
        return f"❌ Could not open URL: {str(e)}"


@function_tool(strict_mode=False)
def get_system_info(category: str) -> str:
    """
    Get information about the local system: OS, CPU, RAM, disk space, Python version.

    Args:
        category: What info to retrieve. Use "all" for everything, or "cpu", "disk", "ram", "os".

    Returns:
        A formatted system information report.
    """
    lines = ["💻 System Information\n"]

    # OS
    lines.append(f"  🖥️  OS: {platform.system()} {platform.release()} ({platform.version()})")
    lines.append(f"  🏗️  Architecture: {platform.machine()}")
    lines.append(f"  👤 User: {os.getenv('USERNAME', os.getenv('USER', 'unknown'))}")
    lines.append(f"  🐍 Python: {sys.version.split()[0]}")

    # CPU
    lines.append(f"  ⚡ Processor: {platform.processor()}")
    lines.append(f"  🧵 CPU Cores: {os.cpu_count()}")

    # Disk space
    try:
        total, used, free = shutil.disk_usage("/")
        lines.append(f"  💾 Disk: {free / (1024**3):.1f} GB free / {total / (1024**3):.1f} GB total")
    except Exception:
        pass

    # Memory (Windows-specific via wmic)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            free_kb = int(result.stdout.strip())
            lines.append(f"  🧠 Free RAM: {free_kb / 1024 / 1024:.1f} GB")
    except Exception:
        pass

    return "\n".join(lines)


@function_tool(strict_mode=False)
def check_process(process_name: str) -> str:
    """
    Check if a process is currently running on the system.

    Args:
        process_name: The name of the process to check (e.g., "chrome", "node", "python").

    Returns:
        Whether the process is running and its details.
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Process -Name '*{process_name}*' -ErrorAction SilentlyContinue | "
             f"Select-Object Name, Id, CPU, WorkingSet64 | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10
        )

        output = result.stdout.strip()
        if output:
            return f"✅ Process '{process_name}' is running:\n{output}"
        else:
            return f"❌ Process '{process_name}' is NOT running."

    except Exception as e:
        return f"❌ Error checking process: {str(e)}"


@function_tool(strict_mode=False)
def close_application(app_name: str) -> str:
    """
    Close a local application by name (ends the process).
    Use this when the user asks to close a window or stop an app.

    Args:
        app_name: Name of the application to close (e.g., "chrome", "code", "notepad").

    Returns:
        Success or error message.
    """
    app_map = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "browser": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "code": "code",
        "vscode": "code",
        "explorer": "explorer",
        "cmd": "cmd",
        "calculator": "calculator",
    }

    app_lower = app_name.lower().strip()
    proc_name = app_map.get(app_lower, app_lower)

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Stop-Process -Name '*{proc_name}*' -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10
        )
        return f"✅ Closed: {app_name}"
    except Exception as e:
        return f"❌ Could not close '{app_name}': {str(e)}"
