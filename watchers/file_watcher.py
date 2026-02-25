#!/usr/bin/env python3
"""File watcher for Personal AI Employee project."""

import os
import sys
import time

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Try watchdog, fallback to polling
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    USE_WATCHDOG = True
except ImportError:
    USE_WATCHDOG = False


class AIFileWatcher:
    """Handles file system events with optional AI summarization."""

    def __init__(self, obsidian_vault: Path, api_key: Optional[str] = None):
        self.obsidian_vault = obsidian_vault
        self.needs_action_dir = obsidian_vault / "Needs_Action"
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.client = None

        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                print("AI summarization enabled")
            except ImportError:
                print("Warning: anthropic package not installed, AI disabled")
                self.client = None

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_file_slug(self, path: str) -> str:
        return Path(path).name.replace(".", "_").replace(" ", "_")

    def log_change(self, event_type: str, path: str) -> None:
        timestamp = self._get_timestamp()
        print(f"[{timestamp}] {event_type.upper()}: {path}")

    def get_ai_summary(self, event_type: str, path: str) -> Optional[str]:
        if not self.client:
            return None

        try:
            file_path = Path(path)
            content = ""
            if file_path.exists() and file_path.is_file():
                content = file_path.read_text(encoding="utf-8")[:2000]

            prompt = f"""Summarize this file change in one sentence.
Event: {event_type}
File: {path}
{"Content preview:" + chr(10) + content if content else "File deleted or empty."}"""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"AI error: {e}"

    def write_obsidian_entry(self, event_type: str, path: str, summary: Optional[str]) -> None:
        timestamp = self._get_timestamp()
        date_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_slug = self._get_file_slug(path)
        filename = f"{date_slug}_{event_type}_{file_slug}.md"

        content = f"""---
timestamp: {timestamp}
event: {event_type}
file: {path}
---

# File Change: {event_type.upper()}

- **Time**: {timestamp}
- **File**: `{path}`
- **Event**: {event_type}

"""
        if summary:
            content += f"""## AI Summary

{summary}
"""

        entry_path = self.needs_action_dir / filename
        entry_path.write_text(content, encoding="utf-8")
        print(f"  -> Obsidian entry: {entry_path}")

    def handle_event(self, event_type: str, path: str) -> None:
        if not path.endswith(".py"):
            return

        self.log_change(event_type, path)
        summary = self.get_ai_summary(event_type, path)
        if summary:
            print(f"  -> AI: {summary}")
        self.write_obsidian_entry(event_type, path, summary)


if USE_WATCHDOG:
    class WatchdogHandler(FileSystemEventHandler):
        def __init__(self, watcher: AIFileWatcher):
            self.watcher = watcher

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher.handle_event("created", event.src_path)

        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher.handle_event("modified", event.src_path)

        def on_deleted(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self.watcher.handle_event("deleted", event.src_path)


def get_file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def scan_files(directories: list[Path]) -> dict[str, str]:
    files = {}
    for directory in directories:
        if not directory.exists():
            continue
        for filepath in directory.rglob("*.py"):
            if filepath.is_file():
                files[str(filepath)] = get_file_hash(filepath)
    return files


def watch_polling(watcher: AIFileWatcher, directories: list[Path], interval: float = 1.0) -> None:
    print("Using polling mode (watchdog not installed)")
    file_hashes = scan_files(directories)
    print(f"Tracking {len(file_hashes)} Python files")
    print("Watching for changes... (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(interval)
            new_hashes = scan_files(directories)

            for path, old_hash in file_hashes.items():
                if path not in new_hashes:
                    watcher.handle_event("deleted", path)
                elif new_hashes[path] != old_hash:
                    watcher.handle_event("modified", path)

            for path in new_hashes:
                if path not in file_hashes:
                    watcher.handle_event("created", path)

            file_hashes = new_hashes

    except KeyboardInterrupt:
        print("\nFile watcher stopped.")


def watch_watchdog(watcher: AIFileWatcher, directories: list[Path]) -> None:
    print("Using watchdog mode")
    handler = WatchdogHandler(watcher)
    observer = Observer()

    for watch_dir in directories:
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)

    observer.start()
    print("Watching for changes... (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nFile watcher stopped.")

    observer.join()


def main() -> None:
    repo_root = Path(__file__).parent.parent
    watch_dirs = [repo_root / "src", repo_root / "tests"]
    obsidian_vault = repo_root / "obsidian_vault"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_file = repo_root / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break

    print("=" * 60)
    print("FILE WATCHER - Personal AI Employee")
    print("=" * 60)
    print(f"Watching: {', '.join(str(d) for d in watch_dirs if d.exists())}")
    print(f"Obsidian: {obsidian_vault}")
    print(f"AI: {'Enabled' if api_key else 'Disabled (no API key)'}")
    print("=" * 60)

    watcher = AIFileWatcher(obsidian_vault, api_key)

    if USE_WATCHDOG:
        watch_watchdog(watcher, watch_dirs)
    else:
        watch_polling(watcher, watch_dirs)


if __name__ == "__main__":
    main()
