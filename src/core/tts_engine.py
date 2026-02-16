"""TTS Engine wrapper for Qwen3-TTS models."""

import torch
import os
from typing import Optional, List, Tuple, Union, Callable, Any
from pathlib import Path
import numpy as np

from utils.error_handler import ModelLoadError, GenerationError, logger


class TTSEngine:
    """Wrapper for Qwen3-TTS models with unified interface."""
    
    # Supported models
    MODELS = {
        "custom_voice_1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "custom_voice_0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "voice_design_1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "base_1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "base_0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    }
    
    # Supported languages
    LANGUAGES = [
        "Auto",
        "Chinese",
        "English",
        "Japanese",
        "Korean",
        "German",
        "French",
        "Russian",
        "Portuguese",
        "Spanish",
        "Italian"
    ]
    
    # Built-in speakers for CustomVoice model
    SPEAKERS = [
        {"name": "Vivian", "description": "Bright, slightly edgy young female voice", "language": "Chinese"},
        {"name": "Serena", "description": "Warm, gentle young female voice", "language": "Chinese"},
        {"name": "Uncle_Fu", "description": "Seasoned male voice with a low, mellow timbre", "language": "Chinese"},
        {"name": "Dylan", "description": "Youthful Beijing male voice with a clear, natural timbre", "language": "Chinese (Beijing)"},
        {"name": "Eric", "description": "Lively Chengdu male voice with a slightly husky brightness", "language": "Chinese (Sichuan)"},
        {"name": "Ryan", "description": "Dynamic male voice with strong rhythmic drive", "language": "English"},
        {"name": "Aiden", "description": "Sunny American male voice with a clear midrange", "language": "English"},
        {"name": "Ono_Anna", "description": "Playful Japanese female voice with a light, nimble timbre", "language": "Japanese"},
        {"name": "Sohee", "description": "Warm Korean female voice with rich emotion", "language": "Korean"}
    ]
    
    def __init__(
        self,
        device: str = "cuda:0",
        dtype: str = "bfloat16",
        use_flash_attention: bool = True,
        workspace_dir: Optional[Path] = None
    ):
        """Initialize TTS engine.
        
        Args:
            device: Compute device ('cuda:0', 'cpu', etc.)
            dtype: Data type ('float16' or 'bfloat16')
            use_flash_attention: Whether to use FlashAttention 2
            workspace_dir: Root workspace directory (for output files, not model cache)
        """
        self.device = device
        self.dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float16
        self.use_flash_attention = use_flash_attention
        self.workspace_dir = workspace_dir
        
        # Note: Models are cached in default HuggingFace cache location (~/.cache/huggingface)
        # Only output files (voices, narrations, etc.) use workspace_dir
        
        # Model instances
        self.custom_voice_model = None
        self.voice_design_model = None
        self.base_model = None
        
        # Check device availability
        self._validate_device()
        
        logger.info(f"TTSEngine initialized with device={device}, dtype={dtype}")
    
    def _validate_device(self) -> None:
        """Validate compute device availability."""
        if "cuda" in self.device:
            if not torch.cuda.is_available():
                logger.warning("CUDA requested but not available. Falling back to CPU.")
                self.device = "cpu"
            else:
                # Check specific device index
                device_id = int(self.device.split(':')[1]) if ':' in self.device else 0
                if device_id >= torch.cuda.device_count():
                    logger.warning(f"CUDA device {device_id} not found. Using cuda:0")
                    self.device = "cuda:0"
    
    @staticmethod
    def get_available_devices() -> List[dict]:
        """Get list of available compute devices.
        
        Returns:
            List of device dictionaries with name and memory info
        """
        devices = [{"id": "cpu", "name": "CPU", "memory": "System RAM"}]
        
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                memory_gb = props.total_memory / (1024**3)
                devices.append({
                    "id": f"cuda:{i}",
                    "name": props.name,
                    "memory": f"{memory_gb:.1f} GB"
                })
        
        return devices
    
    @staticmethod
    def check_device_memory(device: str, required_gb: float = 8.0) -> Tuple[bool, str]:
        """Check if device has sufficient memory.
        
        Args:
            device: Device ID
            required_gb: Required memory in GB
            
        Returns:
            Tuple of (has_sufficient_memory, message)
        """
        if "cuda" in device:
            if not torch.cuda.is_available():
                return False, "CUDA not available"
            
            try:
                device_id = int(device.split(':')[1]) if ':' in device else 0
                props = torch.cuda.get_device_properties(device_id)
                available_gb = props.total_memory / (1024**3)
                
                if available_gb < required_gb:
                    return False, f"Insufficient GPU memory: {available_gb:.1f} GB available, {required_gb:.1f} GB required"
                
                return True, f"Sufficient memory: {available_gb:.1f} GB available"
            except Exception as e:
                return False, f"Error checking device memory: {e}"
        
        # CPU always "has memory" (uses system RAM)
        return True, "CPU will use system RAM"
    
    def load_custom_voice_model(
        self,
        model_size: str = "1.7B",
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Load CustomVoice model for preset speakers.
        
        Args:
            model_size: Model size ('1.7B' or '0.6B')
            progress_callback: Optional callback for progress updates
        """
        try:
            logger.debug(f"Starting CustomVoice model load - size: {model_size}")
            if progress_callback:
                progress_callback(0, f"Loading CustomVoice {model_size} model...")
            
            logger.debug("Importing Qwen3TTSModel...")
            from qwen_tts import Qwen3TTSModel
            
            model_key = f"custom_voice_{model_size}"
            model_name = self.MODELS.get(model_key)
            
            if not model_name:
                raise ModelLoadError(f"Invalid model size: {model_size}")
            
            logger.info(f"Loading model: {model_name}")
            logger.debug(f"Model configuration - device: {self.device}, dtype: {self.dtype}, flash_attn: {self.use_flash_attention}")
            
            attn_impl = "flash_attention_2" if self.use_flash_attention else None
            logger.debug(f"Attention implementation: {attn_impl}")
            
            try:
                logger.debug("Downloading/loading model from HuggingFace...")
                self.custom_voice_model = Qwen3TTSModel.from_pretrained(
                    model_name,
                    device_map=self.device,
                    dtype=self.dtype,
                    attn_implementation=attn_impl
                )
                logger.debug("Model loaded into memory successfully")
            except Exception as e:
                error_str = str(e)
                
                # Handle corrupted cache (symlink issues, incomplete downloads, etc.)
                needs_cache_clear = (
                    "WinError 1314" in error_str or 
                    "required privilege is not held" in error_str or
                    "Can't load feature extractor" in error_str or
                    "preprocessor_config.json" in error_str or
                    "is not a local folder and is not a valid model identifier" in error_str
                )
                
                if needs_cache_clear:
                    logger.error("Corrupted model cache detected - clearing and retrying...")
                    
                    # Try to clear the corrupted model cache
                    cache_dir = Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface'))
                    
                    # Clear from both possible cache locations
                    for cache_subdir in ['hub', 'transformers']:
                        model_cache = cache_dir / cache_subdir / f"models--{model_name.replace('/', '--')}"
                        if model_cache.exists():
                            logger.warning(f"Removing corrupted cache: {model_cache}")
                            try:
                                import shutil
                                shutil.rmtree(model_cache)
                                logger.info(f"Successfully removed cache: {model_cache}")
                            except Exception as rm_err:
                                logger.error(f"Failed to remove cache: {rm_err}")
                    
                    # Set environment to definitely disable symlinks
                    os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
                    
                    # Retry download
                    logger.info("Retrying fresh model download...")
                    self.custom_voice_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=attn_impl
                    )
                    logger.info("Model loaded successfully after cache clear and retry")
                    
                elif "flash_attn" in error_str.lower() and attn_impl == "flash_attention_2":
                    logger.warning("FlashAttention not available, falling back to standard attention")
                    logger.debug("Retrying model load without FlashAttention...")
                    self.custom_voice_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=None
                    )
                    self.use_flash_attention = False
                    logger.debug("Model loaded successfully with standard attention")
                else:
                    raise
            
            if progress_callback:
                progress_callback(100, f"CustomVoice {model_size} model loaded")
            
            logger.info(f"CustomVoice model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load CustomVoice model: {e}")
            raise ModelLoadError(f"Failed to load CustomVoice model: {e}")
    
    def load_voice_design_model(
        self,
        model_size: str = "1.7B",
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Load VoiceDesign model for creating voices from descriptions.
        
        Args:
            model_size: Model size ('1.7B' currently)
            progress_callback: Optional callback for progress updates
        """
        try:
            if progress_callback:
                progress_callback(0, f"Loading VoiceDesign {model_size} model...")
            
            from qwen_tts import Qwen3TTSModel
            
            model_key = f"voice_design_{model_size}"
            model_name = self.MODELS.get(model_key)
            
            if not model_name:
                raise ModelLoadError(f"VoiceDesign model not available for size: {model_size}")
            
            logger.info(f"Loading model: {model_name}")
            
            attn_impl = "flash_attention_2" if self.use_flash_attention else None
            
            try:
                self.voice_design_model = Qwen3TTSModel.from_pretrained(
                    model_name,
                    device_map=self.device,
                    dtype=self.dtype,
                    attn_implementation=attn_impl
                )
            except Exception as e:
                error_str = str(e)
                
                # Handle corrupted cache (symlink issues, incomplete downloads, etc.)
                needs_cache_clear = (
                    "WinError 1314" in error_str or 
                    "required privilege is not held" in error_str or
                    "Can't load feature extractor" in error_str or
                    "preprocessor_config.json" in error_str or
                    "is not a local folder and is not a valid model identifier" in error_str
                )
                
                if needs_cache_clear:
                    logger.error("Corrupted model cache detected - clearing and retrying...")
                    cache_dir = Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface'))
                    
                    # Clear from both possible cache locations
                    for cache_subdir in ['hub', 'transformers']:
                        model_cache = cache_dir / cache_subdir / f"models--{model_name.replace('/', '--')}"
                        if model_cache.exists():
                            logger.warning(f"Removing corrupted cache: {model_cache}")
                            try:
                                import shutil
                                shutil.rmtree(model_cache)
                                logger.info(f"Successfully removed cache: {model_cache}")
                            except Exception as rm_err:
                                logger.error(f"Failed to remove cache: {rm_err}")
                    
                    os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
                    logger.info("Retrying fresh model download...")
                    self.voice_design_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=attn_impl
                    )
                    logger.info("Model loaded successfully after cache clear and retry")
                    
                elif "flash_attn" in error_str.lower() and attn_impl == "flash_attention_2":
                    logger.warning("FlashAttention not available, falling back to standard attention")
                    self.voice_design_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=None
                    )
                    self.use_flash_attention = False
                else:
                    raise
            
            if progress_callback:
                progress_callback(100, f"VoiceDesign {model_size} model loaded")
            
            logger.info(f"VoiceDesign model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load VoiceDesign model: {e}")
            raise ModelLoadError(f"Failed to load VoiceDesign model: {e}")
    
    def load_base_model(
        self,
        model_size: str = "1.7B",
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Load Base model for voice cloning.
        
        Args:
            model_size: Model size ('1.7B' or '0.6B')
            progress_callback: Optional callback for progress updates
        """
        try:
            if progress_callback:
                progress_callback(0, f"Loading Base {model_size} model...")
            
            from qwen_tts import Qwen3TTSModel
            
            model_key = f"base_{model_size}"
            model_name = self.MODELS.get(model_key)
            
            if not model_name:
                raise ModelLoadError(f"Invalid model size: {model_size}")
            
            logger.info(f"Loading model: {model_name}")
            
            attn_impl = "flash_attention_2" if self.use_flash_attention else None
            
            try:
                self.base_model = Qwen3TTSModel.from_pretrained(
                    model_name,
                    device_map=self.device,
                    dtype=self.dtype,
                    attn_implementation=attn_impl
                )
            except Exception as e:
                error_str = str(e)
                
                # Handle corrupted cache (symlink issues, incomplete downloads, etc.)
                needs_cache_clear = (
                    "WinError 1314" in error_str or 
                    "required privilege is not held" in error_str or
                    "Can't load feature extractor" in error_str or
                    "preprocessor_config.json" in error_str or
                    "is not a local folder and is not a valid model identifier" in error_str
                )
                
                if needs_cache_clear:
                    logger.error("Corrupted model cache detected - clearing and retrying...")
                    cache_dir = Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface'))
                    
                    # Clear from both possible cache locations
                    for cache_subdir in ['hub', 'transformers']:
                        model_cache = cache_dir / cache_subdir / f"models--{model_name.replace('/', '--')}"
                        if model_cache.exists():
                            logger.warning(f"Removing corrupted cache: {model_cache}")
                            try:
                                import shutil
                                shutil.rmtree(model_cache)
                                logger.info(f"Successfully removed cache: {model_cache}")
                            except Exception as rm_err:
                                logger.error(f"Failed to remove cache: {rm_err}")
                    
                    os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
                    logger.info("Retrying fresh model download...")
                    self.base_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=attn_impl
                    )
                    logger.info("Model loaded successfully after cache clear and retry")
                    
                elif "flash_attn" in error_str.lower() and attn_impl == "flash_attention_2":
                    logger.warning("FlashAttention not available, falling back to standard attention")
                    self.base_model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map=self.device,
                        dtype=self.dtype,
                        attn_implementation=None
                    )
                    self.use_flash_attention = False
                else:
                    raise
            
            if progress_callback:
                progress_callback(100, f"Base {model_size} model loaded")
            
            logger.info(f"Base model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Base model: {e}")
            raise ModelLoadError(f"Failed to load Base model: {e}")
    
    def generate_custom_voice(
        self,
        text: Union[str, List[str]],
        language: Union[str, List[str]] = "Auto",
        speaker: Union[str, List[str]] = "Ryan",
        instruct: Union[str, List[str]] = "",
        **generation_kwargs
    ) -> Tuple[List[np.ndarray], int]:
        """Generate speech using CustomVoice model with preset speakers.
        
        Args:
            text: Text to synthesize (string or list of strings)
            language: Language(s) for synthesis
            speaker: Speaker name(s)
            instruct: Optional instruction(s) for style control
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (list of audio arrays, sample rate)
        """
        if self.custom_voice_model is None:
            raise GenerationError("CustomVoice model not loaded. Call load_custom_voice_model() first.")
        
        try:
            text_preview = text[:100] if isinstance(text, str) else str(text)[:100]
            text_len = len(text) if isinstance(text, str) else sum(len(t) for t in text)
            logger.info(f"Generating custom voice audio: text_length={text_len}, speaker={speaker}")
            logger.debug(f"Text preview: '{text_preview}...'")
            logger.debug(f"Language: {language}, Instruct: {instruct}")
            logger.debug(f"Generation kwargs: {generation_kwargs}")
            
            # Add default parameters
            if 'max_new_tokens' not in generation_kwargs:
                generation_kwargs['max_new_tokens'] = 2048
            
            logger.info("Starting model inference...")
            import time
            start_time = time.time()
            
            wavs, sr = self.custom_voice_model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruct,
                **generation_kwargs
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Model inference completed in {elapsed:.2f} seconds")
            logger.info(f"Generated {len(wavs)} audio segments at {sr}Hz")
            logger.debug(f"Audio segment shapes: {[w.shape for w in wavs]}")
            return wavs, sr
            
        except Exception as e:
            logger.error(f"Failed to generate custom voice audio: {e}")
            raise GenerationError(f"Failed to generate audio: {e}")
    
    def generate_voice_preset(
        self,
        text: Union[str, List[str]],
        preset_name: str,
        language: Union[str, List[str]] = "Auto",
        instruct: Union[str, List[str]] = "",
        **generation_kwargs
    ) -> Tuple[List[np.ndarray], int]:
        """Generate audio using a built-in preset voice.
        
        This is a convenience wrapper around generate_custom_voice() for library-stored preset voices.
        
        Args:
            text: Text to synthesize (string or list of strings)
            preset_name: Name of preset voice (e.g., "Vivian", "Serena")
            language: Language(s) for synthesis
            instruct: Optional instruction(s) for style control
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (list of audio arrays, sample rate)
        """
        if preset_name not in self.get_supported_speakers():
            raise ValueError(f"Unknown preset voice: {preset_name}. Available: {self.get_supported_speakers()}")
        
        logger.info(f"Generating audio with preset voice: {preset_name}")
        
        # Use generate_custom_voice with the preset speaker name
        return self.generate_custom_voice(
            text=text,
            language=language,
            speaker=preset_name,
            instruct=instruct,
            **generation_kwargs
        )
    
    def generate_voice_design(
        self,
        text: Union[str, List[str]],
        language: Union[str, List[str]] = "Auto",
        instruct: Union[str, List[str]] = "",
        **generation_kwargs
    ) -> Tuple[List[np.ndarray], int]:
        """Generate speech using VoiceDesign model from description.
        
        Args:
            text: Text to synthesize
            language: Language(s) for synthesis
            instruct: Voice description(s)
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (list of audio arrays, sample rate)
        """
        if self.voice_design_model is None:
            raise GenerationError("VoiceDesign model not loaded. Call load_voice_design_model() first.")
        
        try:
            text_preview = text[:100] if isinstance(text, str) else str(text)[:100]
            text_len = len(text) if isinstance(text, str) else sum(len(t) for t in text)
            logger.info(f"Generating voice design audio: text_length={text_len}")
            logger.debug(f"Text preview: '{text_preview}...'")
            logger.debug(f"Language: {language}, Voice description: {instruct}")
            logger.debug(f"Generation kwargs: {generation_kwargs}")
            
            # Add default parameters
            if 'max_new_tokens' not in generation_kwargs:
                generation_kwargs['max_new_tokens'] = 2048
            
            logger.info("Starting model inference...")
            import time
            start_time = time.time()
            
            wavs, sr = self.voice_design_model.generate_voice_design(
                text=text,
                language=language,
                instruct=instruct,
                **generation_kwargs
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Model inference completed in {elapsed:.2f} seconds")
            logger.info(f"Generated {len(wavs)} audio segments at {sr}Hz")
            logger.debug(f"Audio segment shapes: {[w.shape for w in wavs]}")
            return wavs, sr
            
        except Exception as e:
            logger.error(f"Failed to generate voice design audio: {e}")
            raise GenerationError(f"Failed to generate audio: {e}")
    
    def generate_voice_clone(
        self,
        text: Union[str, List[str]],
        language: Union[str, List[str]] = "Auto",
        ref_audio: Optional[Union[str, Tuple[np.ndarray, int]]] = None,
        ref_text: Optional[str] = None,
        voice_clone_prompt: Optional[Any] = None,
        x_vector_only_mode: bool = False,
        **generation_kwargs
    ) -> Tuple[List[np.ndarray], int]:
        """Generate speech using Base model with voice cloning.
        
        Args:
            text: Text to synthesize
            language: Language(s) for synthesis
            ref_audio: Reference audio (path, URL, or (array, sr) tuple)
            ref_text: Reference transcript
            voice_clone_prompt: Pre-built voice clone prompt for reuse
            x_vector_only_mode: Use only speaker embedding (lower quality)
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (list of audio arrays, sample rate)
        """
        if self.base_model is None:
            raise GenerationError("Base model not loaded. Call load_base_model() first.")
        
        try:
            text_preview = text[:100] if isinstance(text, str) else str(text)[:100]
            logger.info(f"Generating voice clone audio: text_length={len(text)}, x_vector_only={x_vector_only_mode}")
            logger.debug(f"Text preview: '{text_preview}...'")
            logger.debug(f"Language: {language}")
            logger.debug(f"Has voice_clone_prompt: {voice_clone_prompt is not None}")
            logger.debug(f"Has ref_audio: {ref_audio is not None}, Has ref_text: {ref_text is not None}")
            logger.debug(f"Generation kwargs: {generation_kwargs}")
            
            # Add default generation parameters if not specified
            if 'max_new_tokens' not in generation_kwargs:
                generation_kwargs['max_new_tokens'] = 2048
                logger.debug(f"Setting default max_new_tokens: 2048")
            if 'temperature' not in generation_kwargs:
                generation_kwargs['temperature'] = 0.7
            if 'do_sample' not in generation_kwargs:
                generation_kwargs['do_sample'] = True
            
            logger.debug(f"Final generation kwargs: {generation_kwargs}")
            logger.info("Starting model inference (this may take 10-60 seconds)...")
            
            import time
            start_time = time.time()
            
            wavs, sr = self.base_model.generate_voice_clone(
                text=text,
                language=language,
                ref_audio=ref_audio,
                ref_text=ref_text,
                voice_clone_prompt=voice_clone_prompt,
                x_vector_only_mode=x_vector_only_mode,
                **generation_kwargs
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Model inference completed in {elapsed:.2f} seconds")
            logger.info(f"Generated {len(wavs)} audio segments at {sr}Hz")
            logger.debug(f"Audio segment shapes: {[w.shape for w in wavs]}")
            return wavs, sr
            
        except Exception as e:
            logger.error(f"Failed to generate voice clone audio: {e}")
            raise GenerationError(f"Failed to generate audio: {e}")
    
    def create_voice_clone_prompt(
        self,
        ref_audio: Union[str, Tuple[np.ndarray, int]],
        ref_text: str = "",
        x_vector_only_mode: bool = False
    ) -> Any:
        """Create reusable voice clone prompt.
        
        Args:
            ref_audio: Reference audio
            ref_text: Reference transcript
            x_vector_only_mode: Use only speaker embedding
            
        Returns:
            Voice clone prompt object for reuse
        """
        if self.base_model is None:
            raise GenerationError("Base model not loaded. Call load_base_model() first.")
        
        try:
            logger.info("Creating voice clone prompt")
            
            prompt = self.base_model.create_voice_clone_prompt(
                ref_audio=ref_audio,
                ref_text=ref_text,
                x_vector_only_mode=x_vector_only_mode
            )
            
            logger.info("Voice clone prompt created successfully")
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to create voice clone prompt: {e}")
            raise GenerationError(f"Failed to create voice clone prompt: {e}")
    
    def get_supported_speakers(self) -> List[str]:
        """Get list of supported speaker names for CustomVoice model.
        
        Returns:
            List of speaker names
        """
        return [s["name"] for s in self.SPEAKERS]
    
    def get_speaker_info(self, speaker_name: str) -> Optional[dict]:
        """Get information about a specific speaker.
        
        Args:
            speaker_name: Name of speaker
            
        Returns:
            Speaker info dictionary or None
        """
        for speaker in self.SPEAKERS:
            if speaker["name"] == speaker_name:
                return speaker
        return None
    
    def unload_model(self, model_type: str) -> None:
        """Unload a specific model to free memory.
        
        Args:
            model_type: Type of model ('custom_voice', 'voice_design', 'base')
        """
        try:
            if model_type == "custom_voice" and self.custom_voice_model is not None:
                del self.custom_voice_model
                self.custom_voice_model = None
                logger.info("CustomVoice model unloaded")
            elif model_type == "voice_design" and self.voice_design_model is not None:
                del self.voice_design_model
                self.voice_design_model = None
                logger.info("VoiceDesign model unloaded")
            elif model_type == "base" and self.base_model is not None:
                del self.base_model
                self.base_model = None
                logger.info("Base model unloaded")
            
            # Clear CUDA cache if using GPU
            if "cuda" in self.device:
                torch.cuda.empty_cache()
                
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    def unload_all_models(self) -> None:
        """Unload all models to free memory."""
        self.unload_model("custom_voice")
        self.unload_model("voice_design")
        self.unload_model("base")
