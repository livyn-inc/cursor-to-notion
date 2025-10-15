#!/usr/bin/env python3

"""
Configuration management for nit CLI
"""

import os
import json
from typing import Dict, Any, Optional
from c2n_core.utils import load_config_for_folder, save_config_for_folder


class ConfigManager:
    """Manages configuration for nit CLI operations"""
    
    def __init__(self, folder: str):
        self.folder = os.path.abspath(folder)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from .c2n/config.json"""
        return load_config_for_folder(self.folder)
    
    def save_config(self) -> None:
        """Save current configuration to .c2n/config.json"""
        save_config_for_folder(self.folder, self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        self.config.update(updates)
    
    # ========================================
    # v2.1: New primary properties
    # ========================================
    
    @property
    def project_url(self) -> Optional[str]:
        """Get project URL (primary sync target, v2.1)"""
        # v2.1: project_url is the primary field
        url = self.get('project_url')
        if url:
            return url
        
        # Backward compatibility: default_parent_url
        return self.get('default_parent_url')
    
    @project_url.setter
    def project_url(self, value: str) -> None:
        """Set project URL (v2.1)"""
        self.set('project_url', value)
    
    @property
    def workspace_url(self) -> Optional[str]:
        """Get workspace URL (optional, for reference, v2.1)"""
        return self.get('workspace_url')
    
    @workspace_url.setter
    def workspace_url(self, value: str) -> None:
        """Set workspace URL (v2.1)"""
        self.set('workspace_url', value)
    
    @property
    def project_name(self) -> Optional[str]:
        """Get project name (v2.1)"""
        return self.get('project_name')
    
    @project_name.setter
    def project_name(self, value: str) -> None:
        """Set project name (v2.1)"""
        self.set('project_name', value)
    
    # ========================================
    # Backward compatibility (deprecated)
    # ========================================
    
    @property
    def default_parent_url(self) -> Optional[str]:
        """Get default parent URL (deprecated, use project_url)"""
        return self.project_url
    
    @default_parent_url.setter
    def default_parent_url(self, value: str) -> None:
        """Set default parent URL (deprecated, use project_url)"""
        self.project_url = value
    
    @property
    def repo_create_url(self) -> Optional[str]:
        """Get repository create URL"""
        return self.get('repo_create_url')
    
    @repo_create_url.setter
    def repo_create_url(self, value: str) -> None:
        """Set repository create URL"""
        self.set('repo_create_url', value)
    
    @property
    def root_page_url(self) -> Optional[str]:
        """Get root page URL"""
        return self.get('root_page_url')
    
    @root_page_url.setter
    def root_page_url(self, value: str) -> None:
        """Set root page URL"""
        self.set('root_page_url', value)
    
    @property
    def pull_apply_default(self) -> bool:
        """Get pull apply default setting"""
        return self.get('pull_apply_default', True)
    
    @pull_apply_default.setter
    def pull_apply_default(self, value: bool) -> None:
        """Set pull apply default setting"""
        self.set('pull_apply_default', value)
    
    @property
    def push_changed_only_default(self) -> bool:
        """Get push changed only default setting"""
        return self.get('push_changed_only_default', True)
    
    @push_changed_only_default.setter
    def push_changed_only_default(self, value: bool) -> None:
        """Set push changed only default setting"""
        self.set('push_changed_only_default', value)
    
    @property
    def sync_mode(self) -> str:
        """Get sync mode (hierarchy or flat)"""
        return self.get('sync_mode', 'hierarchy')
    
    @sync_mode.setter
    def sync_mode(self, value: str) -> None:
        """Set sync mode"""
        self.set('sync_mode', value)
    
    def ensure_config_file(self) -> None:
        """Ensure .c2n/config.json exists with default values (v2.1)"""
        meta_dir = os.path.join(self.folder, '.c2n')
        os.makedirs(meta_dir, exist_ok=True)
        
        config_path = os.path.join(meta_dir, 'config.json')
        if not os.path.exists(config_path):
            import datetime
            default_config = {
                "project_url": "",
                "project_name": "",
                "workspace_url": "",
                "sync_mode": "hierarchy",
                "version": "2.1",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                # Legacy fields for backward compatibility
                "default_parent_url": "",
                "default_title_column": "名前",
                "pull_apply_default": True,
                "push_changed_only_default": True
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            self.config = default_config
        else:
            self.config = self._load_config()
    
    def prompt_for_parent_url(self) -> Optional[str]:
        """Prompt user for parent URL if not set"""
        parent_url = self.default_parent_url
        if not parent_url:
            try:
                parent_url = input("Enter parent Notion page URL: ").strip()
                if parent_url:
                    self.default_parent_url = parent_url
                    self.save_config()
            except (EOFError, KeyboardInterrupt):
                return None
        return parent_url
    
    def validate_config(self) -> bool:
        """Validate current configuration"""
        if not self.default_parent_url and not self.repo_create_url:
            return False
        return True
    
    def get_effective_parent_url(self, override_url: Optional[str] = None) -> Optional[str]:
        """Get effective parent URL (override > default_parent_url > repo_create_url)"""
        if override_url:
            return override_url
        if self.default_parent_url:
            return self.default_parent_url
        if self.repo_create_url:
            return self.repo_create_url
        return None

