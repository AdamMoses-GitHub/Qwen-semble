"""Workspace management for portable mode and centralized data storage."""

import os
import json
from pathlib import Path
from typing import Optional, Tuple

from utils.error_handler import logger
from utils.voice_description_generator import generate_random_voice_descriptions


class WorkspaceManager:
    """Manages workspace directory configuration and setup."""
    
    CONFIG_FILE = Path("working_dir.conf")
    
    def __init__(self):
        """Initialize workspace manager."""
        self.config: Optional[dict] = None
        self.working_dir: Optional[Path] = None
    
    def is_first_launch(self) -> bool:
        """Check if this is the first launch (no config and no working directory).
        
        Returns:
            True if first launch, False otherwise
        """
        if not self.CONFIG_FILE.exists():
            logger.debug("Config file not found - first launch")
            return True
        
        # Load config to check if working directory exists
        try:
            config = self.load_config()
            working_dir = Path(config['working_directory'])
            
            if not working_dir.exists():
                logger.debug("Working directory not found - treating as first launch")
                return True
            
            logger.debug("Config and working directory found - not first launch")
            return False
        except Exception as e:
            logger.error(f"Error checking first launch: {e}")
            return True
    
    def load_config(self) -> dict:
        """Load working directory configuration.
        
        Returns:
            Configuration dictionary with 'working_directory' key
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.CONFIG_FILE.exists():
            raise FileNotFoundError(f"Config file not found: {self.CONFIG_FILE}")
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                path_str = f.read().strip()
            
            if not path_str:
                raise ValueError("Config file is empty")
            
            # Convert to absolute path
            working_dir = Path(path_str).resolve()
            
            self.config = {'working_directory': str(working_dir)}
            logger.info(f"Loaded workspace config: {working_dir}")
            return self.config
            
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            raise ValueError(f"Invalid config file format: {e}")
    
    def save_config(self, working_dir: str) -> None:
        """Save working directory configuration.
        
        Args:
            working_dir: Path to working directory (will be saved as absolute path)
        """
        # Convert to absolute path
        abs_path = Path(working_dir).resolve()
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(str(abs_path))
            
            self.config = {'working_directory': str(abs_path)}
            logger.info(f"Saved workspace config: {abs_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def create_workspace_structure(self, path: Path) -> bool:
        """Create workspace directory structure.
        
        Args:
            path: Path to workspace root
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Creating workspace structure at: {path}")
            
            # Create main directory
            path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories (models cached separately in HuggingFace default cache)
            subdirs = [
                'cloned_voices',
                'designed_voices',
                'narrations',
                'temp',
                'logs'
            ]
            
            for subdir in subdirs:
                (path / subdir).mkdir(exist_ok=True)
                logger.debug(f"Created directory: {subdir}")
            
            # Create default config files if they don't exist
            config_file = path / 'config.json'
            if not config_file.exists():
                # Generate random voice description examples on first launch
                logger.info("Generating random voice description examples...")
                voice_descriptions = generate_random_voice_descriptions(25)
                
                default_config = {
                    "device": "cuda:0",
                    "model_size": "1.7B",
                    "theme": "system",
                    "last_used_speaker": "Ryan",
                    "last_used_language": "Auto",
                    "window_width": 1200,
                    "window_height": 800,
                    "font_size": 100,
                    "use_flash_attention": False,
                    "generation_params": {
                        "max_new_tokens": 2048,
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    "template_test_transcripts": [
                        "I am a voice model. I was created using the magic of computing.",
                        "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                        "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
                    ],
                    "example_voice_descriptions": voice_descriptions
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                logger.debug(f"Created default config.json with {len(voice_descriptions)} random voice examples")
            
            voice_lib_file = path / 'voice_library.json'
            if not voice_lib_file.exists():
                with open(voice_lib_file, 'w', encoding='utf-8') as f:
                    json.dump({"cloned_voices": [], "designed_voices": []}, f, indent=2)
                logger.debug("Created default voice_library.json")
            
            logger.info("Workspace structure created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create workspace structure: {e}")
            return False
    
    def validate_workspace(self, path: Path) -> Tuple[bool, str]:
        """Validate workspace directory.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if path is valid
        try:
            path = Path(path).resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"
        
        # Check if we can create/write to the directory
        if path.exists():
            if not path.is_dir():
                return False, "Path exists but is not a directory"
            if not os.access(path, os.W_OK):
                return False, "Directory is not writable (permission denied)"
        else:
            # Try to create parent to test permissions
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(path.parent, os.W_OK):
                    return False, "Cannot create directory (permission denied)"
            except Exception as e:
                return False, f"Cannot create directory: {e}"
        
        return True, ""
    
    def get_working_directory(self) -> Path:
        """Get the current working directory path.
        
        Returns:
            Path to working directory
            
        Raises:
            ValueError: If config not loaded or invalid
        """
        if self.working_dir:
            return self.working_dir
        
        if not self.config:
            self.config = self.load_config()
        
        working_dir = Path(self.config['working_directory'])
        
        self.working_dir = working_dir
        return working_dir
    
    def get_config_file(self) -> Path:
        """Get path to config.json file.
        
        Returns:
            Path to config.json
        """
        return self.get_working_directory() / "config.json"
    
    def get_voice_library_file(self) -> Path:
        """Get path to voice_library.json file.
        
        Returns:
            Path to voice_library.json
        """
        return self.get_working_directory() / "voice_library.json"
    
    def get_cloned_voices_dir(self) -> Path:
        """Get path to cloned voices directory.
        
        Creates directory if it doesn't exist.
        
        Returns:
            Path to cloned_voices directory
        """
        dir_path = self.get_working_directory() / "cloned_voices"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_designed_voices_dir(self) -> Path:
        """Get path to designed voices directory.
        
        Creates directory if it doesn't exist.
        
        Returns:
            Path to designed_voices directory
        """
        dir_path = self.get_working_directory() / "designed_voices"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_narrations_dir(self) -> Path:
        """Get path to narrations output directory.
        
        Creates directory if it doesn't exist.
        
        Returns:
            Path to narrations directory
        """
        dir_path = self.get_working_directory() / "narrations"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_temp_dir(self) -> Path:
        """Get path to temporary files directory.
        
        Creates directory if it doesn't exist.
        
        Returns:
            Path to temp directory
        """
        dir_path = self.get_working_directory() / "temp"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_logs_dir(self) -> Path:
        """Get path to logs directory.
        
        Creates directory if it doesn't exist.
        
        Returns:
            Path to logs directory
        """
        dir_path = self.get_working_directory() / "logs"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_hf_token_file(self) -> Path:
        """Get path to HuggingFace token file.
        
        Returns:
            Path to huggingface_token.txt
        """
        return self.get_working_directory() / "huggingface_token.txt"
    
    def get_estimated_space_gb(self) -> Tuple[float, float]:
        """Get estimated disk space requirements for workspace.
        
        Note: Models are cached separately in HuggingFace default cache (~/.cache/huggingface)
        and require an additional ~7-14GB depending on model size.
        
        Returns:
            Tuple of (minimum_gb, recommended_gb) for workspace only
        """
        # Voice data: ~1GB per 100 voices (estimate)
        # Narrations: varies widely, ~100MB-1GB typical
        # Logs and temp: ~100MB
        # Config files: negligible
        
        minimum_gb = 2.0  # Minimum for basic workspace files
        recommended_gb = 5.0  # Recommended for comfortable use
        
        return minimum_gb, recommended_gb
