"""
Atomic file operations for SpecKit Agent System.

This module provides safe, atomic file write operations using the
temp file + validate + os.replace pattern to prevent partial writes
and data corruption.
"""

from pathlib import Path
from typing import Optional, Callable
import tempfile
import os
import re


class FileOperationError(Exception):
    """Raised when a file operation fails."""
    pass


def atomic_write(
    file_path: Path,
    content: str,
    encoding: str = 'utf-8',
    validator: Optional[Callable[[str], bool]] = None,
    create_dirs: bool = True
) -> None:
    """
    Atomically write content to a file using temp file + validate + rename pattern.

    This ensures that either the complete content is written successfully,
    or the original file remains unchanged. Prevents partial writes and corruption.

    Args:
        file_path: Destination file path
        content: Content to write
        encoding: File encoding (default: utf-8)
        validator: Optional validation function that takes content and returns bool
        create_dirs: If True, create parent directories if they don't exist

    Raises:
        FileOperationError: If write or validation fails
    """
    file_path = Path(file_path)

    # Create parent directories if needed
    if create_dirs and not file_path.parent.exists():
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileOperationError(f"Failed to create parent directories: {e}")

    # Run validator before writing if provided
    if validator:
        try:
            if not validator(content):
                raise FileOperationError("Content validation failed before write")
        except Exception as e:
            raise FileOperationError(f"Validation error: {e}")

    # Create temporary file in the same directory as target file
    # This ensures atomic rename on the same filesystem
    temp_fd = None
    temp_path = None

    try:
        # Create temp file in same directory
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp"
        )
        temp_path = Path(temp_path_str)

        # Write content to temp file
        with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        temp_fd = None  # Closed by context manager

        # Validate written content if validator provided
        if validator:
            try:
                written_content = temp_path.read_text(encoding=encoding)
                if not validator(written_content):
                    raise FileOperationError("Content validation failed after write")
            except Exception as e:
                raise FileOperationError(f"Post-write validation error: {e}")

        # Atomically replace the target file
        # os.replace is atomic on POSIX systems
        os.replace(temp_path, file_path)
        temp_path = None  # Successfully moved

    except Exception as e:
        # Clean up temp file if it still exists
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except Exception:
                pass

        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

        raise FileOperationError(f"Atomic write failed for {file_path}: {e}")


def validate_no_placeholders(content: str) -> bool:
    """
    Validate that content has no unresolved template placeholders.

    Args:
        content: Content to validate

    Returns:
        True if no placeholders found, False otherwise
    """
    # Check for common placeholder patterns
    patterns = [
        r'{{[A-Z_]+}}',  # {{PLACEHOLDER}}
        r'\[.*?PLACEHOLDER.*?\]',  # [PLACEHOLDER]
        r'TODO:',  # TODO markers
        r'FIXME:',  # FIXME markers
        r'TBD',  # TBD markers
        r'NEEDS CLARIFICATION',  # Explicit needs clarification markers
    ]

    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False

    return True


def validate_yaml_frontmatter(content: str) -> bool:
    """
    Validate that content has valid YAML frontmatter.

    Args:
        content: Content to validate

    Returns:
        True if frontmatter is valid, False otherwise
    """
    if not content.strip():
        return False

    # Check for frontmatter delimiters
    if not content.startswith('---\n'):
        return False

    # Find closing delimiter
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return False

    # Basic YAML structure validation
    frontmatter = parts[1]

    # Check for required fields (at minimum, should have key: value pairs)
    if ':' not in frontmatter:
        return False

    return True


def validate_markdown_structure(content: str) -> bool:
    """
    Validate that content has basic markdown structure.

    Args:
        content: Content to validate

    Returns:
        True if structure is valid, False otherwise
    """
    if not content.strip():
        return False

    # Should have at least one heading
    if not re.search(r'^#+\s+.+$', content, re.MULTILINE):
        return False

    # Should have some content beyond just headings
    non_heading_content = re.sub(r'^#+\s+.+$', '', content, flags=re.MULTILINE)
    if len(non_heading_content.strip()) < 10:
        return False

    return True


def safe_read(
    file_path: Path,
    encoding: str = 'utf-8',
    default: Optional[str] = None
) -> Optional[str]:
    """
    Safely read file content with error handling.

    Args:
        file_path: File to read
        encoding: File encoding
        default: Default value to return if file doesn't exist

    Returns:
        File content, or default value if file doesn't exist

    Raises:
        FileOperationError: If read fails for reasons other than file not existing
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return default

    try:
        return file_path.read_text(encoding=encoding)
    except Exception as e:
        raise FileOperationError(f"Failed to read {file_path}: {e}")


def safe_copy(
    source_path: Path,
    dest_path: Path,
    overwrite: bool = False
) -> None:
    """
    Safely copy a file with error handling.

    Args:
        source_path: Source file
        dest_path: Destination file
        overwrite: If True, overwrite destination if it exists

    Raises:
        FileOperationError: If copy fails
    """
    source_path = Path(source_path)
    dest_path = Path(dest_path)

    if not source_path.exists():
        raise FileOperationError(f"Source file does not exist: {source_path}")

    if dest_path.exists() and not overwrite:
        raise FileOperationError(f"Destination file already exists: {dest_path}")

    try:
        # Create parent directories if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Read source
        content = source_path.read_text(encoding='utf-8')

        # Write to destination atomically
        atomic_write(dest_path, content)

    except Exception as e:
        raise FileOperationError(f"Failed to copy {source_path} to {dest_path}: {e}")


def ensure_directory(dir_path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        dir_path: Directory path to ensure

    Raises:
        FileOperationError: If directory creation fails
    """
    dir_path = Path(dir_path)

    if dir_path.exists():
        if not dir_path.is_dir():
            raise FileOperationError(f"Path exists but is not a directory: {dir_path}")
        return

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise FileOperationError(f"Failed to create directory {dir_path}: {e}")


def create_validator(
    *validators: Callable[[str], bool]
) -> Callable[[str], bool]:
    """
    Create a combined validator from multiple validator functions.

    Args:
        *validators: Validator functions to combine

    Returns:
        Combined validator that returns True only if all validators pass
    """
    def combined_validator(content: str) -> bool:
        return all(validator(content) for validator in validators)

    return combined_validator
