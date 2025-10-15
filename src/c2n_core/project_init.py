"""
Common project initialization logic for init and clone commands.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Any

__all__ = ["initialize_project", "DEFAULT_IGNORE_TEMPLATE"]


DEFAULT_IGNORE_TEMPLATE = """# Notion sync ignore patterns (gitignore-style)

# Build artifacts
build/
dist/
*.pyc
__pycache__/

# Temporary files
*.tmp
*.log
.DS_Store

# IDE files
.vscode/
.idea/

# Personal notes
_private/
notes/

# Node modules
node_modules/

# Image files (not supported for upload)
*.png
*.jpg
*.jpeg
*.gif
*.bmp
*.webp
*.svg
*.ico
"""


def initialize_project(folder: str, root_url: str, workspace_url: Optional[str] = None) -> None:
    """
    Initialize a project with .c2n configuration (common for init/clone) (v2.1).
    
    Args:
        folder: Project folder path
        root_url: Notion project page URL
        workspace_url: Notion workspace URL (parent of project page) - optional
    
    Creates:
        - .c2n/config.json (with project_url and optionally workspace_url)
        - .c2n/index.yaml
        - .c2n_ignore
    
    v2.1 changes:
        - Stores project_url instead of default_parent_url
        - Stores workspace_url if provided
    """
    # 1. Create directories
    os.makedirs(folder, exist_ok=True)
    c2n_dir = os.path.join(folder, ".c2n")
    os.makedirs(c2n_dir, exist_ok=True)
    
    # 2. Create config.json (v2.1: project_url + workspace_url)
    config: Dict[str, Any] = {
        "project_url": root_url,
        "sync_mode": "hierarchy"
    }
    
    if workspace_url:
        config["workspace_url"] = workspace_url
    
    config_path = os.path.join(c2n_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # 3. Create index.yaml (initial structure)
    # Using basic YAML format to avoid pyyaml dependency
    # items must be dict (not list) for directory_processor.py compatibility
    index_content = f"""root_page_url: {root_url}
items: {{}}
"""
    
    index_path = os.path.join(c2n_dir, "index.yaml")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    
    # 4. Create .c2n_ignore if it doesn't exist
    ignore_path = os.path.join(folder, ".c2n_ignore")
    if not os.path.exists(ignore_path):
        with open(ignore_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_IGNORE_TEMPLATE)


def get_config_template() -> Dict[str, Any]:
    """
    Get the default config template for v2.0.
    
    Returns:
        Dictionary with default configuration
    """
    return {
        "default_parent_url": "",
        "sync_mode": "hierarchy"
    }

