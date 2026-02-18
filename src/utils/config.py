"""Configuration management for Qwen-semble application."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager

from utils.voice_description_generator import generate_random_voice_descriptions


class Config:
    """Application configuration manager."""
    
    def __init__(self, workspace_mgr: 'WorkspaceManager'):
        """Initialize configuration manager.
        
        Args:
            workspace_mgr: WorkspaceManager instance
        """
        self.workspace_mgr = workspace_mgr
        self.config_path = workspace_mgr.get_config_file()
        self.config: Dict[str, Any] = {}
        
        # Configuration defaults
        self.defaults = {
            "device": "cuda:0",
            "model_size": "1.7B",
            "theme": "dark",
            "last_used_speaker": "Ryan",
            "last_used_language": "Auto",
            "window_width": 1200,
            "window_height": 800,
            "font_size": 100,
            "use_flash_attention": True,
            "downloaded_models": [],  # List of downloaded models: ["1.7B", "0.6B"]
            "active_model": None,  # Currently active model: "1.7B" or "0.6B"
            "generation_params": {
                "max_new_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "repetition_penalty": 1.0
            },
            "template_test_transcripts": [
                "I am a voice model. I was created using the magic of computing.",
                "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
            ],
            "example_voice_descriptions": []  # Generated randomly on first launch
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
            
            # Generate example voice descriptions if empty
            if not self.config.get("example_voice_descriptions"):
                self.config["example_voice_descriptions"] = generate_random_voice_descriptions(25)
                self.save()
                
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            self.config = self.defaults.copy()
    
    def _merge_defaults(self) -> None:
        """Merge default values for any missing configuration keys."""
        updated = False
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(self.config[key], dict):
                # Merge nested dictionaries
                for subkey, subvalue in value.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = subvalue
                        updated = True
        
        # Save config if new defaults were added
        if updated:
            self.save()
    
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
    
    def regenerate_voice_descriptions(self, count: int = 25) -> None:
        """Regenerate random voice description examples.
        
        Args:
            count: Number of descriptions to generate (default: 25)
        """
        self.config["example_voice_descriptions"] = generate_random_voice_descriptions(count)
        self.save()
