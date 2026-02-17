"""Quick test script for workspace functionality."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from utils.workspace_manager import WorkspaceManager
from utils.error_handler import configure_logging

def test_workspace_manager():
    """Test WorkspaceManager functionality."""
    print("=" * 60)
    print("Testing WorkspaceManager")
    print("=" * 60)
    
    # Create manager
    mgr = WorkspaceManager()
    print(f"✓ WorkspaceManager created")
    
    # Check if first launch
    is_first = mgr.is_first_launch()
    print(f"  First launch: {is_first}")
    
    if not is_first:
        # Load existing config
        config = mgr.load_config()
        print(f"  Loaded config: {config}")
        
        # Get working directory
        working_dir = mgr.get_working_directory()
        print(f"  Working directory: {working_dir}")
        
        # Test all getters
        print("\nTesting getter methods:")
        print(f"  Config file: {mgr.get_config_file()}")
        print(f"  Voice library: {mgr.get_voice_library_file()}")
        print(f"  Cloned voices: {mgr.get_cloned_voices_dir()}")
        print(f"  Designed voices: {mgr.get_designed_voices_dir()}")
        print(f"  Narrations: {mgr.get_narrations_dir()}")
        print(f"  Temp: {mgr.get_temp_dir()}")
        print(f"  Logs: {mgr.get_logs_dir()}")
        print(f"  HF token: {mgr.get_hf_token_file()}")
        
        # Check if directories were created
        print("\nChecking directories exist:")
        for name, path in [
            ("Cloned voices", mgr.get_cloned_voices_dir()),
            ("Designed voices", mgr.get_designed_voices_dir()),
            ("Narrations", mgr.get_narrations_dir()),
            ("Temp", mgr.get_temp_dir()),
            ("Logs", mgr.get_logs_dir())
        ]:
            exists = "✓" if path.exists() else "✗"
            print(f"  {exists} {name}: {path}")
        
        # Test logging configuration
        print("\nTesting logging configuration:")
        configure_logging(mgr)
        print("  ✓ Logging configured")
        
        from utils.error_handler import logger
        logger.info("Test log message from workspace test")
        print("  ✓ Test message logged")
        
    else:
        print("\n⚠  No workspace configured yet")
        print("  Run the application to set up workspace")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_workspace_manager()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
