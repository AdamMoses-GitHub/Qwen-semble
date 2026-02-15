"""Audio utilities for playback and file operations."""

import soundfile as sf
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Callable
import threading

from utils.error_handler import AudioValidationError, logger


class AudioPlayer:
    """Audio playback manager with state control."""
    
    # Class-level registry to track all instances
    _all_players = []
    _registry_lock = threading.Lock()
    
    def __init__(self):
        """Initialize audio player."""
        self.is_playing_flag = False
        self.current_audio = None
        self.current_sr = None
        self.stop_event = threading.Event()
        self.playback_thread = None
        
        # Register this instance
        with AudioPlayer._registry_lock:
            AudioPlayer._all_players.append(self)
    
    @classmethod
    def stop_all(cls) -> None:
        """Stop all audio players application-wide."""
        with cls._registry_lock:
            for player in cls._all_players:
                if player.is_playing_flag:
                    player.stop()
    
    def play(self, audio: np.ndarray, sample_rate: int, callback: Optional[Callable] = None) -> None:
        """Play audio with optional completion callback.
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            callback: Optional function to call when playback completes
        """
        # Stop ALL audio players application-wide before starting new playback
        logger.debug(f"Starting audio playback - sample_rate: {sample_rate}Hz, duration: {len(audio)/sample_rate:.2f}s")
        AudioPlayer.stop_all()
        
        self.current_audio = audio
        self.current_sr = sample_rate
        self.is_playing_flag = True
        self.stop_event.clear()
        
        self.current_audio = audio
        self.current_sr = sample_rate
        self.is_playing_flag = True
        self.stop_event.clear()
        
        def _play_thread():
            try:
                logger.debug("Playing audio through sounddevice...")
                sd.play(audio, sample_rate)
                sd.wait()
                
                if not self.stop_event.is_set():
                    logger.info("Audio playback completed")
                    if callback:
                        logger.debug("Calling playback completion callback")
                        callback()
            except Exception as e:
                logger.error(f"Error during audio playback: {e}")
            finally:
                self.is_playing_flag = False
                logger.debug("Playback thread finished")
        
        self.playback_thread = threading.Thread(target=_play_thread, daemon=True)
        self.playback_thread.start()
    
    def stop(self) -> None:
        """Stop current audio playback."""
        if self.is_playing_flag:
            logger.debug("Stopping audio playback")
            self.stop_event.set()
            sd.stop()
            self.is_playing_flag = False
            logger.info("Audio playback stopped")
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing.
        
        Returns:
            True if audio is playing, False otherwise
        """
        return self.is_playing_flag


def save_audio(audio: np.ndarray, sample_rate: int, filepath: str) -> None:
    """Save audio to WAV file.
    
    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate in Hz
        filepath: Output file path
    """
    try:
        logger.debug(f"Saving audio to: {filepath}")
        logger.debug(f"Audio properties - shape: {audio.shape}, sr: {sample_rate}Hz, duration: {len(audio)/sample_rate:.2f}s")
        
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Save as WAV file
        sf.write(filepath, audio, sample_rate)
        file_size = Path(filepath).stat().st_size / 1024  # Size in KB
        logger.info(f"Audio saved to: {filepath} ({file_size:.1f} KB)")
        
    except Exception as e:
        logger.error(f"Failed to save audio: {e}")
        raise AudioValidationError(f"Failed to save audio: {e}")


def load_audio(filepath: str) -> Tuple[np.ndarray, int]:
    """Load audio from file.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Tuple of (audio data, sample rate)
    """
    try:
        logger.debug(f"Loading audio from: {filepath}")
        audio, sr = sf.read(filepath)
        duration = len(audio)/sr
        file_size = Path(filepath).stat().st_size / 1024  # Size in KB
        logger.info(f"Audio loaded from: {filepath} (sr={sr}, duration={duration:.2f}s, size={file_size:.1f}KB)")
        logger.debug(f"Audio shape: {audio.shape}")
        return audio, sr
        
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        raise AudioValidationError(f"Failed to load audio: {e}")


def get_audio_duration(filepath: str) -> float:
    """Get duration of audio file in seconds.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Duration in seconds
    """
    try:
        info = sf.info(filepath)
        return info.duration
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
        return 0.0


def get_audio_info(filepath: str) -> dict:
    """Get detailed information about audio file.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Dictionary with audio information
    """
    try:
        info = sf.info(filepath)
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "subtype": info.subtype
        }
    except Exception as e:
        logger.error(f"Failed to get audio info: {e}")
        return {}


def validate_audio_file(filepath: str) -> Tuple[bool, str]:
    """Validate audio file for TTS operations.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(filepath)
    
    # Check file exists
    if not path.exists():
        return False, f"File not found: {filepath}"
    
    # Check file extension
    valid_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    if path.suffix.lower() not in valid_extensions:
        return False, f"Unsupported format. Use: {', '.join(valid_extensions)}"
    
    try:
        # Try to read file info
        info = sf.info(filepath)
        
        # Check sample rate
        if info.samplerate < 16000:
            return False, f"Sample rate too low ({info.samplerate} Hz). Use at least 16kHz."
        
        # Check duration
        if info.duration < 1.0:
            return False, f"Audio too short ({info.duration:.1f}s). Use at least 1 second."
        
        if info.duration > 120.0:
            return False, f"Audio too long ({info.duration:.1f}s). Use under 2 minutes."
        
        return True, ""
        
    except Exception as e:
        return False, f"Cannot read audio file: {str(e)}"


def merge_audio_segments(
    segments: list[np.ndarray],
    sample_rate: int,
    silence_duration: float = 0.3
) -> np.ndarray:
    """Merge multiple audio segments with silence between them.
    
    Args:
        segments: List of audio arrays
        sample_rate: Sample rate in Hz
        silence_duration: Duration of silence between segments in seconds
        
    Returns:
        Merged audio array
    """
    logger.debug(f"Merging {len(segments)} audio segments with {silence_duration}s silence")
    
    if not segments:
        logger.warning("merge_audio_segments called with empty segments list")
        return np.array([])
    
    if len(segments) == 1:
        logger.debug("Only one segment, returning as-is")
        return segments[0]
    
    # Create silence
    silence_samples = int(silence_duration * sample_rate)
    silence = np.zeros(silence_samples)
    logger.debug(f"Silence buffer: {silence_samples} samples")
    
    # Merge segments with silence
    merged = []
    for i, segment in enumerate(segments):
        logger.debug(f"Adding segment {i+1}/{len(segments)} - {len(segment)} samples")
        merged.append(segment)
        if i < len(segments) - 1:  # Don't add silence after last segment
            merged.append(silence)
    
    result = np.concatenate(merged)
    total_duration = len(result)/sample_rate
    logger.info(f"Merged {len(segments)} segments into {total_duration:.2f}s audio ({len(result)} samples)")
    return result


def normalize_audio(audio: np.ndarray, target_level: float = -3.0) -> np.ndarray:
    """Normalize audio to target dB level.
    
    Args:
        audio: Audio data
        target_level: Target level in dB
        
    Returns:
        Normalized audio
    """
    logger.debug(f"Normalizing audio to {target_level} dB")
    
    # Calculate current peak level in dB
    peak = np.abs(audio).max()
    if peak == 0:
        logger.warning("Audio is silent (peak = 0), skipping normalization")
        return audio
    
    current_db = 20 * np.log10(peak)
    logger.debug(f"Current peak level: {current_db:.2f} dB")
    
    # Calculate required gain
    gain_db = target_level - current_db
    gain_linear = 10 ** (gain_db / 20)
    logger.debug(f"Applying gain: {gain_db:.2f} dB (linear: {gain_linear:.4f})")
    
    # Apply gain
    normalized = audio * gain_linear
    
    # Clip to prevent overflow
    normalized = np.clip(normalized, -1.0, 1.0)
    
    return normalized


def convert_to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert stereo audio to mono.
    
    Args:
        audio: Audio data (can be mono or stereo)
        
    Returns:
        Mono audio
    """
    if len(audio.shape) == 1:
        # Already mono
        return audio
    elif len(audio.shape) == 2:
        # Stereo - average channels
        return audio.mean(axis=1)
    else:
        raise ValueError(f"Unsupported audio shape: {audio.shape}")
