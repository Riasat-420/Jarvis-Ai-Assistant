"""
Jarvis AI Assistant — File Operations Tool
Read, write, list, and search files with path validation.
"""

import os
import glob
from pathlib import Path
from agents import function_tool
from config import ALLOWED_DIRECTORIES, MAX_OUTPUT_LENGTH


def _is_path_allowed(filepath: str) -> bool:
    """Check if a file path is within allowed directories."""
    target = Path(filepath).resolve()
    for allowed_dir in ALLOWED_DIRECTORIES:
        try:
            target.relative_to(allowed_dir.resolve())
            return True
        except ValueError:
            continue
    return False


@function_tool(strict_mode=False)
def read_file(filepath: str) -> str:
    """
    Read the contents of a file. Only works for files in allowed directories
    (Desktop, Documents, Downloads, and the Jarvis project folder).

    Args:
        filepath: The absolute or relative path to the file to read.

    Returns:
        The file contents, or an error message.
    """
    try:
        resolved = Path(filepath).resolve()
        if not _is_path_allowed(str(resolved)):
            return f"🚫 Access denied: {filepath} is outside allowed directories."

        if not resolved.exists():
            return f"❌ File not found: {filepath}"

        if not resolved.is_file():
            return f"❌ Not a file: {filepath}"

        # Check file size (don't read files > 1MB)
        size = resolved.stat().st_size
        if size > 1_000_000:
            return f"⚠️ File too large ({size:,} bytes). Max: 1MB."

        content = resolved.read_text(encoding="utf-8", errors="replace")

        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + f"\n... (truncated, {len(content)} total chars)"

        return content

    except Exception as e:
        return f"❌ Error reading file: {type(e).__name__}: {str(e)}"


@function_tool(strict_mode=False)
def write_file(filepath: str, content: str) -> str:
    """
    Write content to a file. Creates the file if it doesn't exist.
    Only works for files in allowed directories.

    Args:
        filepath: The path where the file should be written.
        content: The text content to write to the file.

    Returns:
        A success or error message.
    """
    try:
        resolved = Path(filepath).resolve()
        if not _is_path_allowed(str(resolved)):
            return f"🚫 Access denied: {filepath} is outside allowed directories."

        # Create parent directories if needed
        resolved.parent.mkdir(parents=True, exist_ok=True)

        resolved.write_text(content, encoding="utf-8")
        return f"✅ File written successfully: {resolved} ({len(content)} chars)"

    except Exception as e:
        return f"❌ Error writing file: {type(e).__name__}: {str(e)}"


@function_tool(strict_mode=False)
def list_directory(directory: str) -> str:
    """
    List contents of a directory with file sizes and types.

    Args:
        directory: The path to the directory to list.

    Returns:
        A formatted listing of the directory contents.
    """
    try:
        resolved = Path(directory).resolve()
        if not _is_path_allowed(str(resolved)):
            return f"🚫 Access denied: {directory} is outside allowed directories."

        if not resolved.exists():
            return f"❌ Directory not found: {directory}"

        if not resolved.is_dir():
            return f"❌ Not a directory: {directory}"

        entries = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines = [f"📁 Contents of: {resolved}\n"]

        for entry in entries[:100]:  # Limit to 100 entries
            if entry.is_dir():
                child_count = sum(1 for _ in entry.iterdir()) if entry.exists() else 0
                lines.append(f"  📂 {entry.name}/ ({child_count} items)")
            else:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024*1024):.1f} MB"
                lines.append(f"  📄 {entry.name} ({size_str})")

        if len(list(resolved.iterdir())) > 100:
            lines.append(f"\n  ... and more (showing first 100)")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error listing directory: {type(e).__name__}: {str(e)}"


@function_tool(strict_mode=False)
def search_files(directory: str, pattern: str) -> str:
    """
    Search for files matching a glob pattern within a directory.

    Args:
        directory: The directory to search in.
        pattern: Glob pattern to match (e.g., "*.py", "**/*.html", "readme*").

    Returns:
        A list of matching file paths.
    """
    try:
        resolved = Path(directory).resolve()
        if not _is_path_allowed(str(resolved)):
            return f"🚫 Access denied: {directory} is outside allowed directories."

        if not resolved.is_dir():
            return f"❌ Not a directory: {directory}"

        matches = list(resolved.glob(pattern))[:50]  # Limit to 50 results

        if not matches:
            return f"No files found matching '{pattern}' in {directory}"

        lines = [f"🔍 Found {len(matches)} file(s) matching '{pattern}':\n"]
        for match in matches:
            rel_path = match.relative_to(resolved)
            lines.append(f"  → {rel_path}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error searching: {type(e).__name__}: {str(e)}"
