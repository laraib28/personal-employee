#!/usr/bin/env python3
"""
AI-Connected File Watcher for SpecKit Agent System.

Watches for file changes and triggers AI analysis using Claude API.
Reports issues, suggests improvements, and can auto-fix problems.
"""

import os
import sys
import time
import hashlib
import difflib
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file contents."""
    try:
        return hashlib.md5(filepath.read_bytes()).hexdigest()
    except Exception:
        return ""


def get_file_content(filepath: Path) -> str:
    """Get file contents safely."""
    try:
        return filepath.read_text(encoding='utf-8')
    except Exception:
        return ""


def scan_files(directories: list[Path], extensions: tuple = ('.py',)) -> dict:
    """Scan directories for files and return hash map with content."""
    files = {}
    for directory in directories:
        if not directory.exists():
            continue
        for filepath in directory.rglob('*'):
            if filepath.is_file() and filepath.suffix in extensions:
                files[str(filepath)] = {
                    'hash': get_file_hash(filepath),
                    'content': get_file_content(filepath)
                }
    return files


def analyze_with_ai(filepath: str, old_content: str, new_content: str, api_key: str) -> Optional[dict]:
    """Analyze file changes using Claude API."""
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Generate diff
        diff = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            lineterm=''
        ))
        diff_text = ''.join(diff[:100])  # Limit diff size

        if not diff_text.strip():
            return None

        prompt = f"""Analyze this Python code change and provide brief feedback.

File: {filepath}

Diff:
```diff
{diff_text}
```

Provide a brief analysis (2-3 sentences max) covering:
1. What changed
2. Any potential issues (bugs, security, style)
3. One suggestion if applicable

Format: Start with an emoji indicating status:
- ✅ Good change
- ⚠️ Needs attention
- ❌ Potential issue
- 💡 Suggestion

Keep response under 100 words."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            'analysis': response.content[0].text.strip(),
            'file': filepath,
            'lines_changed': len([l for l in diff if l.startswith('+') or l.startswith('-')])
        }

    except Exception as e:
        return {'error': str(e), 'file': filepath}


def analyze_new_file(filepath: str, content: str, api_key: str) -> Optional[dict]:
    """Analyze a newly added file."""
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Truncate large files
        content_preview = content[:2000] if len(content) > 2000 else content

        prompt = f"""Briefly analyze this new Python file.

File: {filepath}

```python
{content_preview}
```

Provide a one-line summary of what this file does and any immediate concerns.
Format: emoji + brief description (under 50 words)

Emojis: ✅ Good | ⚠️ Needs attention | ❌ Issue | 📄 Info"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            'analysis': response.content[0].text.strip(),
            'file': filepath,
            'type': 'new_file'
        }

    except Exception as e:
        return {'error': str(e), 'file': filepath}


def watch_with_ai(directories: list[Path], api_key: str, interval: float = 2.0):
    """Watch directories and analyze changes with AI."""
    print("=" * 60)
    print("AI-CONNECTED FILE WATCHER")
    print("=" * 60)
    print(f"Watching: {', '.join(str(d) for d in directories)}")
    print(f"AI Model: Claude Sonnet")
    print(f"Interval: {interval}s")
    print("=" * 60)

    # Initial scan
    file_data = scan_files(directories)
    print(f"Tracking {len(file_data)} Python files")
    print("=" * 60)
    print("Waiting for changes... (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(interval)

            # Rescan
            new_data = scan_files(directories)
            timestamp = datetime.now().strftime('%H:%M:%S')

            # Check for changes
            for filepath, old_info in file_data.items():
                if filepath not in new_data:
                    print(f"[{timestamp}] 🗑️  REMOVED: {filepath}")
                elif new_data[filepath]['hash'] != old_info['hash']:
                    print(f"[{timestamp}] 📝 CHANGED: {filepath}")
                    print(f"[{timestamp}] 🤖 Analyzing with AI...")

                    result = analyze_with_ai(
                        filepath,
                        old_info['content'],
                        new_data[filepath]['content'],
                        api_key
                    )

                    if result:
                        if 'error' in result:
                            print(f"[{timestamp}] ⚠️  AI Error: {result['error']}")
                        else:
                            print(f"[{timestamp}] 🤖 AI: {result['analysis']}")
                    print()

            # Check for new files
            for filepath in new_data:
                if filepath not in file_data:
                    print(f"[{timestamp}] ✨ ADDED: {filepath}")
                    print(f"[{timestamp}] 🤖 Analyzing new file...")

                    result = analyze_new_file(
                        filepath,
                        new_data[filepath]['content'],
                        api_key
                    )

                    if result:
                        if 'error' in result:
                            print(f"[{timestamp}] ⚠️  AI Error: {result['error']}")
                        else:
                            print(f"[{timestamp}] 🤖 AI: {result['analysis']}")
                    print()

            # Update cache
            file_data = new_data

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] AI file watcher stopped.")


def main():
    # Get API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        # Try loading from .env file
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"\'')
                    break

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found")
        print("Set it via environment variable or in .env file")
        sys.exit(1)

    # Directories to watch
    repo_root = Path(__file__).parent.parent
    watch_dirs = [
        repo_root / 'src',
        repo_root / 'tests',
    ]

    # Filter to existing directories
    watch_dirs = [d for d in watch_dirs if d.exists()]

    if not watch_dirs:
        print("Error: No directories to watch found")
        sys.exit(1)

    watch_with_ai(watch_dirs, api_key, interval=2.0)


if __name__ == '__main__':
    main()
