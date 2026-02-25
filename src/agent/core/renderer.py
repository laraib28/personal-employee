"""
Template rendering engine for SpecKit Agent System.

This module provides Jinja2-based template rendering with custom filters
for generating specifications, plans, tasks, and other artifacts.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import re
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


class RenderError(Exception):
    """Raised when template rendering fails."""
    pass


class Renderer:
    """
    Template rendering engine with custom filters.

    Loads templates from .specify/templates/ and provides rendering
    with custom filters for slugification, date formatting, and ID allocation.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the renderer.

        Args:
            template_dir: Template directory. If None, uses .specify/templates/
        """
        if template_dir is None:
            template_dir = Path.cwd() / ".specify" / "templates"

        self.template_dir = Path(template_dir)

        if not self.template_dir.exists():
            raise RenderError(f"Template directory not found: {self.template_dir}")

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # We're generating markdown, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        # Register custom filters
        self.env.filters['slugify'] = self.slugify
        self.env.filters['iso_date'] = self.iso_date
        self.env.filters['allocate_id'] = self.allocate_id
        self.env.filters['format_list'] = self.format_list
        self.env.filters['indent'] = self.indent_text

    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to URL-friendly slug.

        Args:
            text: Text to slugify

        Returns:
            Slugified text
        """
        # Convert to lowercase
        slug = text.lower()

        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Replace multiple consecutive hyphens with single hyphen
        slug = re.sub(r'-+', '-', slug)

        return slug

    @staticmethod
    def iso_date(date: Optional[datetime] = None) -> str:
        """
        Format date as ISO 8601 date string (YYYY-MM-DD).

        Args:
            date: Date to format. If None, uses current date.

        Returns:
            ISO formatted date string
        """
        if date is None:
            date = datetime.now()

        return date.strftime("%Y-%m-%d")

    def allocate_id(
        self,
        directory: Path,
        prefix: str = "",
        suffix: str = "",
        digits: int = 3
    ) -> str:
        """
        Allocate next available ID by scanning directory.

        Args:
            directory: Directory to scan for existing IDs
            prefix: File prefix before ID number
            suffix: File suffix after ID number
            digits: Number of digits for ID (default: 3)

        Returns:
            Next available ID as zero-padded string
        """
        directory = Path(directory)

        if not directory.exists():
            # Directory doesn't exist yet, return first ID
            return "0" * (digits - 1) + "1"

        max_id = 0

        # Scan directory for files matching pattern
        pattern = f"{prefix}*{suffix}"
        for file_path in directory.glob(pattern):
            filename = file_path.name

            # Remove prefix and suffix
            if prefix:
                filename = filename[len(prefix):]
            if suffix:
                filename = filename[:-len(suffix)] if suffix else filename

            # Extract numeric ID
            match = re.match(r'^(\d+)', filename)
            if match:
                file_id = int(match.group(1))
                max_id = max(max_id, file_id)

        # Return next ID
        next_id = max_id + 1
        return str(next_id).zfill(digits)

    @staticmethod
    def format_list(items: list, bullet: str = "-", indent: int = 0) -> str:
        """
        Format a list as markdown bullet points.

        Args:
            items: List items to format
            bullet: Bullet character (default: -)
            indent: Number of spaces to indent (default: 0)

        Returns:
            Formatted markdown list
        """
        if not items:
            return ""

        indent_str = " " * indent
        lines = [f"{indent_str}{bullet} {item}" for item in items]
        return "\n".join(lines)

    @staticmethod
    def indent_text(text: str, spaces: int = 2) -> str:
        """
        Indent all lines of text by specified number of spaces.

        Args:
            text: Text to indent
            spaces: Number of spaces to indent

        Returns:
            Indented text
        """
        indent = " " * spaces
        lines = text.split("\n")
        return "\n".join(f"{indent}{line}" if line else line for line in lines)

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Template filename (e.g., "spec-template.md")
            context: Dictionary of template variables

        Returns:
            Rendered template content

        Raises:
            RenderError: If template not found or rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(context)

        except TemplateNotFound:
            raise RenderError(f"Template not found: {template_name}")
        except Exception as e:
            raise RenderError(f"Failed to render template '{template_name}': {e}")

    def render_string(
        self,
        template_string: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Template content as string
            context: Dictionary of template variables

        Returns:
            Rendered content

        Raises:
            RenderError: If rendering fails
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(context)

        except Exception as e:
            raise RenderError(f"Failed to render template string: {e}")

    def get_template_path(self, template_name: str) -> Optional[Path]:
        """
        Get the full path to a template file.

        Args:
            template_name: Template filename

        Returns:
            Path to template, or None if not found
        """
        template_path = self.template_dir / template_name

        if template_path.exists():
            return template_path

        return None

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Template filename

        Returns:
            True if template exists
        """
        return self.get_template_path(template_name) is not None


def get_renderer(template_dir: Optional[Path] = None) -> Renderer:
    """
    Get a renderer instance.

    Args:
        template_dir: Optional template directory

    Returns:
        Renderer instance
    """
    return Renderer(template_dir)


def render_template(
    template_name: str,
    context: Dict[str, Any],
    template_dir: Optional[Path] = None
) -> str:
    """
    Convenience function to render a template.

    Args:
        template_name: Template filename
        context: Template variables
        template_dir: Optional template directory

    Returns:
        Rendered content
    """
    renderer = Renderer(template_dir)
    return renderer.render_template(template_name, context)


def slugify(text: str) -> str:
    """
    Convenience function to slugify text.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    return Renderer.slugify(text)


def iso_date(date: Optional[datetime] = None) -> str:
    """
    Convenience function to format date as ISO string.

    Args:
        date: Date to format (default: now)

    Returns:
        ISO formatted date
    """
    return Renderer.iso_date(date)
