"""Error handling and validation utilities."""

import logging
from pathlib import Path
from typing import Tuple, Optional, TYPE_CHECKING
import traceback

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager


# Logger will be configured after workspace is determined
logger = logging.getLogger('Qwen-semble')


def configure_logging(workspace_mgr: 'WorkspaceManager'):
    """Configure logging with workspace-aware paths.
    
    Args:
        workspace_mgr: WorkspaceManager instance to get log directory
    """
    # Get log directory from workspace manager
    log_dir = workspace_mgr.get_logs_dir()
    
    log_file = log_dir / "app.log"
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Configure logging with DEBUG level for verbose output
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    logger.info(f"Logging configured: {log_file}")


# Note: Logger is initially unconfigured (no file output)
# configure_logging() must be called after WorkspaceManager is initialized


class QwenTTSError(Exception):
    """Base exception for Qwen-semble application."""
    pass


class ModelLoadError(QwenTTSError):
    """Error loading TTS model."""
    pass


class AudioValidationError(QwenTTSError):
    """Error validating audio file."""
    pass


class GenerationError(QwenTTSError):
    """Error during audio generation."""
    pass


def validate_audio_for_cloning(filepath: str) -> Tuple[bool, str]:
    """Validate audio file for voice cloning.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(filepath)
        
        # Check file exists
        if not path.exists():
            return False, f"File not found: {filepath}"
        
        # Check file is readable
        if not path.is_file():
            return False, f"Not a file: {filepath}"
        
        # Check file extension
        valid_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
        if path.suffix.lower() not in valid_extensions:
            return False, f"Unsupported audio format. Please use: {', '.join(valid_extensions)}"
        
        # Try to read audio file to validate format
        try:
            import soundfile as sf
            data, samplerate = sf.read(filepath)
            
            # Check sample rate
            if samplerate < 16000:
                return False, f"Sample rate too low ({samplerate} Hz). Please use audio with at least 16kHz sample rate."
            
            # Check duration
            duration = len(data) / samplerate
            if duration < 1.0:
                return False, f"Audio too short ({duration:.1f}s). Please use audio of at least 1 second."
            
            if duration < 3.0:
                logger.warning(f"Audio is short ({duration:.1f}s). 3-60 seconds recommended for best results.")
            
            if duration > 120.0:
                return False, f"Audio too long ({duration:.1f}s). Please use audio under 2 minutes."
            
            return True, ""
            
        except Exception as e:
            return False, f"Cannot read audio file: {str(e)}"
            
    except Exception as e:
        return False, f"Error validating audio: {str(e)}"


def validate_transcript(text: str, max_length: int = 100000) -> Tuple[bool, str]:
    """Validate transcript text.
    
    Args:
        text: Transcript text
        max_length: Maximum allowed character length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Transcript is empty"
    
    if len(text) > max_length:
        return False, f"Transcript too long ({len(text)} characters). Maximum is {max_length}."
    
    return True, ""


def get_user_friendly_error(error: Exception) -> str:
    """Convert exception to user-friendly error message.
    
    Args:
        error: Exception object
        
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    # GPU out of memory
    if 'out of memory' in error_str or 'cuda' in error_str and 'memory' in error_str:
        return (
            "GPU out of memory. Try one of these solutions:\n"
            "1. Close other applications using GPU\n"
            "2. Switch to CPU in Settings (slower but works)\n"
            "3. Use the 0.6B model instead of 1.7B\n"
            "4. Reduce text length"
        )
    
    # CUDA not available
    if 'cuda' in error_str and ('unavailable' in error_str or 'not available' in error_str):
        return (
            "CUDA (GPU support) is not available. The application will use CPU.\n"
            "To enable GPU acceleration:\n"
            "1. Install CUDA toolkit\n"
            "2. Install PyTorch with CUDA support\n"
            "3. Restart the application"
        )
    
    # Network/download errors
    if 'connection' in error_str or 'timeout' in error_str or 'download' in error_str:
        return (
            "Failed to download model. Please check:\n"
            "1. Internet connection is working\n"
            "2. HuggingFace token is valid (if required)\n"
            "3. Try again in a few minutes"
        )
    
    # Model not found
    if 'model' in error_str and 'not found' in error_str:
        return (
            "Model not found. This may be due to:\n"
            "1. Invalid model name\n"
            "2. Model requires authentication (add HuggingFace token in Settings)\n"
            "3. Network issues preventing download"
        )
    
    # Audio file errors
    if 'audio' in error_str or 'soundfile' in error_str:
        return (
            "Audio file error. Please ensure:\n"
            "1. File is a valid audio format (WAV, MP3, FLAC)\n"
            "2. File is not corrupted\n"
            "3. File is accessible (not locked by another program)"
        )
    
    # Generic error with trace
    return f"An error occurred: {str(error)}\n\nPlease check the log file for details."


def log_error(error: Exception, context: str = "") -> None:
    """Log error with full traceback.
    
    Args:
        error: Exception object
        context: Additional context about where error occurred
    """
    logger.error(f"Error in {context}: {str(error)}")
    logger.error(traceback.format_exc())


def show_error_dialog(error: Exception, context: str = "", parent=None) -> None:
    """Show error dialog to user (requires customtkinter).
    
    Args:
        error: Exception object
        context: Context where error occurred
        parent: Parent window for dialog
    """
    try:
        from tkinter import messagebox
        
        title = f"Error: {context}" if context else "Error"
        message = get_user_friendly_error(error)
        
        messagebox.showerror(title, message, parent=parent)
        log_error(error, context)
        
    except ImportError:
        # Fallback if GUI not available
        print(f"ERROR: {get_user_friendly_error(error)}")
        log_error(error, context)


def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise
