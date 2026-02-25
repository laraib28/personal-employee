"""
Setup script for SpecKit Agent System.

This file provides backward compatibility for projects that use setup.py.
Modern projects should rely on pyproject.toml for configuration.
"""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Read the long description from README
long_description = (here / "README.md").read_text(encoding="utf-8") if (here / "README.md").exists() else ""

setup(
    name="speckit-agent",
    version="0.1.0",
    description="AI Agent System for Spec-Driven Development with constitution-compliant workflow execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="SpecKit Team",
    author_email="team@speckit.dev",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=[
        "anthropic>=0.40.0",
        "Jinja2>=3.1.0",
        "PyYAML>=6.0",
        "GitPython>=3.1.0",
        "click>=8.0",
        "markdown-it-py>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-mock>=3.10",
            "black>=23.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "speckit-agent=agent.cli:main",
        ],
    },
    include_package_data=True,
)
