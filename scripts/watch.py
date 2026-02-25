#!/usr/bin/env python3
"""
Simple file watcher for SpecKit Agent System.

Watches src/ and tests/ directories for Python file changes
and reports modified files. Can be extended to run tests on change.
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file contents."""
    try:
        return hashlib.md5(filepath.read_bytes()).hexdigest()
    except Exception:
        return ""


def scan_files(directories: list[Path], extensions: tuple = ('.py',)) -> dict:
    """Scan directories for files and return hash map."""
    files = {}
    for directory in directories:
        if not directory.exists():
            continue
        for filepath in directory.rglob('*'):
            if filepath.is_file() and filepath.suffix in extensions:
                files[str(filepath)] = get_file_hash(filepath)
    return files


def watch(directories: list[Path], interval: float = 1.0):
    """Watch directories for changes."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting file watcher...")
    print(f"Watching: {', '.join(str(d) for d in directories)}")
    print(f"Interval: {interval}s")
    print("-" * 60)

    # Initial scan
    file_hashes = scan_files(directories)
    print(f"Tracking {len(file_hashes)} files")
    print("-" * 60)
    print("Waiting for changes... (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(interval)

            # Rescan
            new_hashes = scan_files(directories)

            # Check for changes
            changed = []
            added = []
            removed = []

            # Check for modified and removed files
            for filepath, old_hash in file_hashes.items():
                if filepath not in new_hashes:
                    removed.append(filepath)
                elif new_hashes[filepath] != old_hash:
                    changed.append(filepath)

            # Check for new files
            for filepath in new_hashes:
                if filepath not in file_hashes:
                    added.append(filepath)

            # Report changes
            timestamp = datetime.now().strftime('%H:%M:%S')

            for f in added:
                print(f"[{timestamp}] + ADDED: {f}")

            for f in removed:
                print(f"[{timestamp}] - REMOVED: {f}")

            for f in changed:
                print(f"[{timestamp}] * CHANGED: {f}")

            if changed or added or removed:
                print(f"[{timestamp}] --- {len(changed)} changed, {len(added)} added, {len(removed)} removed ---\n")

            # Update hashes
            file_hashes = new_hashes

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] File watcher stopped.")


if __name__ == '__main__':
    # Default directories to watch
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

    watch(watch_dirs, interval=1.0)
