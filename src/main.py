"""Main entry point for Qwen-semble TTS Voice Studio."""

import sys
import os
import multiprocessing
from pathlib import Path

# Suppress HuggingFace symlink warning on Windows
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
# Disable symlinks entirely on Windows (requires admin privileges otherwise)
os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'

# Add src to path for imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.workspace_manager import WorkspaceManager
from utils.error_handler import logger, configure_logging
from gui.app import run


def setup_workspace():
    """Set up workspace directory and return WorkspaceManager instance.
    
    Returns:
        WorkspaceManager instance, or None if user cancelled setup
    """
    workspace_mgr = WorkspaceManager()
    
    # Check if this is first launch
    if workspace_mgr.is_first_launch():
        logger.info("First launch detected - showing workspace setup dialog")
        
        # Show workspace setup dialog
        from gui.workspace_setup_dialog import show_workspace_setup_dialog
        result = show_workspace_setup_dialog()
        
        if result is None:
            # User cancelled setup
            logger.info("Workspace setup cancelled by user")
            return None
        
        logger.info(f"Workspace configured: {result['path']}")
        
    else:
        # Load existing workspace configuration
        config = workspace_mgr.load_config()
        workspace_path = Path(config['working_directory'])
        logger.info(f"Using existing workspace: {workspace_path}")
        
        # Validate workspace still exists and is valid
        is_valid, error_msg = workspace_mgr.validate_workspace(workspace_path)
        if not is_valid:
            logger.error(f"Workspace validation failed: {error_msg}")
            logger.error("Cannot continue without valid workspace")
            return None
    
    return workspace_mgr


def main():
    """Main entry point."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Qwen-semble TTS Voice Studio")
        logger.info("Verbose logging enabled (DEBUG level)")
        logger.info("=" * 60)
        
        # Set multiprocessing start method for Windows + PyTorch compatibility
        if sys.platform == 'win32':
            multiprocessing.set_start_method('spawn', force=True)
        
        # Setup workspace
        logger.debug("Setting up workspace...")
        workspace_mgr = setup_workspace()
        
        if workspace_mgr is None:
            # User cancelled or workspace setup failed
            logger.error("Cannot start application without workspace")
            print("\n\nApplication requires a workspace directory to run.")
            print("Please restart and select a valid workspace location.")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Configure logging with workspace path
        configure_logging(workspace_mgr)
        logger.info(f"Using workspace: {workspace_mgr.get_working_directory()}")
        
        # Run application
        logger.debug("Launching GUI application...")
        run(workspace_mgr)
        
        logger.info("Application exited normally")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n\nFATAL ERROR: {e}\n")
        print("Check logs for details.")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
