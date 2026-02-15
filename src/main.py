"""Main entry point for Qwen-semble TTS Voice Studio."""

import sys
import os
import multiprocessing
from pathlib import Path

# Suppress HuggingFace symlink warning on Windows
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# Add src to path for imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.error_handler import logger, ensure_directory
from gui.app import run


def setup_environment():
    """Set up application environment."""
    # Set multiprocessing start method for Windows + PyTorch compatibility
    if sys.platform == 'win32':
        multiprocessing.set_start_method('spawn', force=True)
    
    # Ensure required directories exist
    directories = [
        "output",
        "output/cloned_voices",
        "output/designed_voices",
        "output/narrations",
        "output/temp",
        "output/logs",
        "config",
        "models"
    ]
    
    for directory in directories:
        ensure_directory(directory)
    
    logger.info("Environment setup complete")


def main():
    """Main entry point."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Qwen-semble TTS Voice Studio")
        logger.info("Verbose logging enabled (DEBUG level)")
        logger.info("=" * 60)
        
        # Setup environment
        logger.debug("Starting environment setup...")
        setup_environment()
        
        # Run application
        logger.debug("Launching GUI application...")
        run()
        
        logger.info("Application exited normally")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n\nFATAL ERROR: {e}\n")
        print("Check output/logs/app.log for details.")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
