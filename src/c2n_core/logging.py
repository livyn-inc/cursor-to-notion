"""YAML logging and dependency management utilities."""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, Optional


__all__ = [
    "load_yaml_file",
    "save_yaml_file",
    "check_yaml_available",
    "check_dependency",
    "ensure_dependency",
    "get_yaml_fallback_message",
]


def check_yaml_available() -> bool:
    """Check if PyYAML is available."""
    try:
        import yaml  # type: ignore
        return True
    except ImportError:
        return False


def load_yaml_file(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load YAML file with fallback to default if PyYAML is not available."""
    if not os.path.exists(file_path):
        return default or {}
    
    if not check_yaml_available():
        print_warning(f"PyYAML not available, using fallback for {file_path}")
        return default or {}
    
    try:
        import yaml  # type: ignore
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print_warning(f"Failed to load YAML file {file_path}: {e}")
        return default or {}


def save_yaml_file(file_path: str, data: Dict[str, Any]) -> bool:
    """Save YAML file with fallback if PyYAML is not available."""
    if not check_yaml_available():
        print_warning(f"PyYAML not available, using fallback for {file_path}")
        # Fallback: save as string representation
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(data))
            return True
        except Exception as e:
            print_error(f"Failed to save fallback file {file_path}: {e}")
            return False
    
    try:
        import yaml  # type: ignore
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e:
        print_error(f"Failed to save YAML file {file_path}: {e}")
        return False


def check_dependency(module_name: str) -> bool:
    """Check if a Python module is available."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def ensure_dependency(module_name: str, package_name: Optional[str] = None) -> bool:
    """Ensure a dependency is available, with helpful error message."""
    if check_dependency(module_name):
        return True
    
    package = package_name or module_name
    print_error(f"{package} is not installed. Please run: pip install {package}")
    return False


def get_yaml_fallback_message() -> str:
    """Get a consistent message for YAML fallback."""
    return "PyYAML not available, using fallback"


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"Warning: {message}", file=sys.stderr)


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"Error: {message}", file=sys.stderr)


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}
    
    # Find end of frontmatter
    yaml_end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            yaml_end = i
            break
    
    if yaml_end <= 0:
        return {}
    
    frontmatter_text = '\n'.join(lines[1:yaml_end])
    
    if not check_yaml_available():
        # Fallback: simple key-value parsing
        result = {}
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                result[key] = value
        return result
    
    try:
        import yaml  # type: ignore
        return yaml.safe_load(frontmatter_text) or {}
    except Exception:
        # Fallback to simple parsing
        result = {}
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                result[key] = value
        return result





