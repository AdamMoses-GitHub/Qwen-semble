"""Workspace management for portable mode and centralized data storage."""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from utils.error_handler import logger


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
            working_dir = self.resolve_path(config['working_directory'], config['path_type'])
            
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
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.CONFIG_FILE.exists():
            raise FileNotFoundError(f"Config file not found: {self.CONFIG_FILE}")
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required fields
            required = ['working_directory', 'path_type']
            for field in required:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            self.config = config
            logger.info(f"Loaded workspace config: {config['working_directory']} ({config['path_type']})")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise ValueError(f"Invalid config file format: {e}")
    
    def save_config(self, working_dir: str, path_type: str, use_local_token: bool = False) -> None:
        """Save working directory configuration.
        
        Args:
            working_dir: Path to working directory
            path_type: 'relative' or 'absolute'
            use_local_token: Whether to store HuggingFace token in workspace
        """
        config = {
            "working_directory": working_dir,
            "path_type": path_type,
            "created": datetime.now().isoformat(),
            "use_local_hf_token": use_local_token
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            self.config = config
            logger.info(f"Saved workspace config: {working_dir} ({path_type})")
            
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
                    }
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                logger.debug("Created default config.json")
            
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
    
    def migrate_existing_data(self, workspace_dir: Path) -> Tuple[bool, str]:
        """Migrate data from old structure to workspace.
        
        Args:
            workspace_dir: Destination workspace directory
            
        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info("Starting data migration to workspace")
            
            # Define migration mappings
            migrations = [
                (Path("output/cloned_voices"), workspace_dir / "cloned_voices"),
                (Path("output/designed_voices"), workspace_dir / "designed_voices"),
                (Path("output/narrations"), workspace_dir / "narrations"),
                (Path("output/logs"), workspace_dir / "logs"),
                (Path("config/app_config.json"), workspace_dir / "config.json"),
                (Path("config/voice_library.json"), workspace_dir / "voice_library.json"),
            ]
            
            migrated_items = []
            
            for source, dest in migrations:
                if not source.exists():
                    logger.debug(f"Source not found, skipping: {source}")
                    continue
                
                try:
                    if source.is_dir():
                        # Copy directory contents
                        if dest.exists():
                            # Merge with existing
                            shutil.copytree(source, dest, dirs_exist_ok=True)
                        else:
                            shutil.copytree(source, dest)
                        logger.info(f"Migrated directory: {source} -> {dest}")
                    else:
                        # Copy file
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, dest)
                        logger.info(f"Migrated file: {source} -> {dest}")
                    
                    migrated_items.append(source.name)
                    
                except Exception as e:
                    logger.error(f"Failed to migrate {source}: {e}")
                    # Continue with other items
            
            if migrated_items:
                message = f"Migrated {len(migrated_items)} items: {', '.join(migrated_items)}"
                logger.info(f"Migration completed: {message}")
                return True, message
            else:
                logger.info("No data to migrate")
                return True, "No existing data found to migrate"
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False, f"Migration failed: {e}"
    
    def detect_existing_data(self) -> bool:
        """Check if old data structure exists.
        
        Returns:
            True if old data found, False otherwise
        """
        old_paths = [
            Path("output"),
            Path("config/app_config.json"),
            Path("config/voice_library.json")
        ]
        
        for path in old_paths:
            if path.exists():
                logger.debug(f"Found existing data: {path}")
                return True
        
        return False
    
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
        
        working_dir = self.resolve_path(
            self.config['working_directory'],
            self.config['path_type']
        )
        
        self.working_dir = working_dir
        return working_dir
    
    def resolve_path(self, path_str: str, path_type: str) -> Path:
        """Resolve path based on type.
        
        Args:
            path_str: Path string
            path_type: 'relative' or 'absolute'
            
        Returns:
            Resolved Path object
        """
        path = Path(path_str)
        
        if path_type == 'relative':
            # Resolve relative to application directory
            app_dir = Path(__file__).parent.parent.parent
            return (app_dir / path).resolve()
        else:
            return path.resolve()
    
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
