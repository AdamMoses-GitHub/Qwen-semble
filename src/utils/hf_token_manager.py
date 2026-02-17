"""HuggingFace token management for local and global storage."""

import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager

from utils.error_handler import logger


class HFTokenManager:
    """Manage HuggingFace authentication tokens."""
    
    def __init__(self, workspace_mgr: 'WorkspaceManager', use_local: bool = False):
        """Initialize token manager.
        
        Args:
            workspace_mgr: WorkspaceManager instance
            use_local: Whether to use local token storage
        """
        self.workspace_mgr = workspace_mgr
        self.use_local = use_local
        self.token_file = workspace_mgr.get_hf_token_file()
    
    def get_token(self) -> Optional[str]:
        """Get HuggingFace token from appropriate location.
        
        Returns:
            Token string or None if not found
        """
        if self.use_local:
            # Try local token first
            token = self._read_local_token()
            if token:
                logger.debug("Using local HuggingFace token from workspace")
                return token
            # Fall back to global if local not found
            logger.debug("Local token not found, falling back to global")
        
        # Use global token (HuggingFace Hub default)
        token = self._read_global_token()
        if token:
            logger.debug("Using global HuggingFace token")
        else:
            logger.debug("No HuggingFace token found")
        
        return token
    
    def _read_local_token(self) -> Optional[str]:
        """Read token from workspace directory.
        
        Returns:
            Token string or None
        """
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                    if token:
                        return token
        except Exception as e:
            logger.error(f"Error reading local token: {e}")
        
        return None
    
    def _read_global_token(self) -> Optional[str]:
        """Read token from HuggingFace Hub global storage.
        
        Returns:
            Token string or None
        """
        try:
            from huggingface_hub import HfFolder
            token = HfFolder.get_token()
            return token
        except ImportError:
            logger.warning("huggingface_hub not available")
            return None
        except Exception as e:
            logger.error(f"Error reading global token: {e}")
            return None
    
    def save_token(self, token: str) -> bool:
        """Save token to appropriate location.
        
        Args:
            token: HuggingFace token string
            
        Returns:
            True if successful, False otherwise
        """
        if self.use_local:
            return self._save_local_token(token)
        else:
            return self._save_global_token(token)
    
    def _save_local_token(self, token: str) -> bool:
        """Save token to workspace directory.
        
        Args:
            token: HuggingFace token string
            
        Returns:
            True if successful
        """
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'w', encoding='utf-8') as f:
                f.write(token)
            
            # Set restrictive permissions on Unix systems
            if os.name != 'nt':  # Not Windows
                os.chmod(self.token_file, 0o600)
            
            logger.info("Saved HuggingFace token to workspace")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save local token: {e}")
            return False
    
    def _save_global_token(self, token: str) -> bool:
        """Save token to HuggingFace Hub global storage.
        
        Args:
            token: HuggingFace token string
            
        Returns:
            True if successful
        """
        try:
            from huggingface_hub import login
            login(token=token)
            logger.info("Saved HuggingFace token globally")
            return True
            
        except ImportError:
            logger.error("huggingface_hub not available")
            return False
        except Exception as e:
            logger.error(f"Failed to save global token: {e}")
            return False
    
    def delete_local_token(self) -> bool:
        """Delete token from workspace directory.
        
        Returns:
            True if successful or file doesn't exist
        """
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Deleted local HuggingFace token")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete local token: {e}")
            return False
    
    def delete_global_token(self) -> bool:
        """Delete token from HuggingFace Hub global storage.
        
        Returns:
            True if successful
        """
        try:
            from huggingface_hub import logout
            logout()
            logger.info("Deleted global HuggingFace token")
            return True
            
        except ImportError:
            logger.error("huggingface_hub not available")
            return False
        except Exception as e:
            logger.error(f"Failed to delete global token: {e}")
            return False
    
    def switch_storage_mode(self, to_local: bool, token: Optional[str] = None) -> bool:
        """Switch between local and global token storage.
        
        Args:
            to_local: True to switch to local, False for global
            token: Optional token to transfer (if None, reads from current location)
            
        Returns:
            True if successful
        """
        try:
            # Get current token if not provided
            if token is None:
                token = self.get_token()
                if not token:
                    logger.warning("No token found to transfer")
                    self.use_local = to_local
                    return True
            
            # Save to new location
            old_mode = self.use_local
            self.use_local = to_local
            
            if not self.save_token(token):
                # Revert on failure
                self.use_local = old_mode
                return False
            
            # Optionally delete from old location
            # (We'll keep it as backup for now)
            
            logger.info(f"Switched token storage mode to: {'local' if to_local else 'global'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch storage mode: {e}")
            return False
    
    def is_token_available(self) -> bool:
        """Check if a token is available.
        
        Returns:
            True if token found
        """
        return self.get_token() is not None
