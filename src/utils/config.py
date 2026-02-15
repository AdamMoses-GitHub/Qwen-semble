"""Configuration management for Qwen-semble application."""

import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Application configuration manager."""
    
    def __init__(self, config_path: str = "config/app_config.json"):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.defaults = {
            "device": "cuda:0",
            "model_size": "1.7B",
            "theme": "dark",
            "output_dir": "output/",
            "models_cache_dir": "",
            "last_used_speaker": "Ryan",
            "last_used_language": "Auto",
            "window_width": 1200,
            "window_height": 800,
            "font_size": 100,
            "use_flash_attention": True,
            "generation_params": {
                "max_new_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        self.load()
    
    def load(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # Merge with defaults for any missing keys
                self._merge_defaults()
            else:
                self.config = self.defaults.copy()
                self.save()
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            self.config = self.defaults.copy()
    
    def _merge_defaults(self) -> None:
        """Merge default values for any missing configuration keys."""
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict) and isinstance(self.config[key], dict):
                # Merge nested dictionaries
                for subkey, subvalue in value.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = subvalue
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
            save: Whether to save configuration immediately
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        
        if save:
            self.save()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self.config = self.defaults.copy()
        self.save()
