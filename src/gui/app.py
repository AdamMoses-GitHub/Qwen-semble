"""Main application window with tabbed interface."""

import customtkinter as ctk
from tkinter import messagebox
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager

from core.tts_engine import TTSEngine
from core.voice_library import VoiceLibrary
from core.audio_utils import AudioPlayer
from utils.config import Config
from utils.error_handler import logger
from utils.threading_helpers import run_in_thread

from gui.tab_voice_creation import VoiceCreationTab
from gui.tab_narration import NarrationTab
from gui.tab_settings import SettingsTab
from gui.tab_saved_voices import SavedVoicesTab
from gui.components import LoadingOverlay


class QwenTTSApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self, workspace_mgr: 'WorkspaceManager'):
        """Initialize main application.
        
        Args:
            workspace_mgr: WorkspaceManager instance
        """
        super().__init__()
        
        self.workspace_mgr = workspace_mgr
        
        # Configure window
        self.title("Qwen-semble - TTS Voice Studio")
        
        # Load configuration
        self.config = Config(workspace_mgr=workspace_mgr)
        window_width = self.config.get("window_width", 1200)
        window_height = self.config.get("window_height", 800)
        self.geometry(f"{window_width}x{window_height}")
        
        # Set theme
        theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        logger.debug(f"UI theme set to: {theme}")
        
        # Initialize components
        logger.debug("Initializing application components...")
        self.tts_engine = None
        self.voice_library = VoiceLibrary(workspace_mgr=workspace_mgr)
        self.audio_player = AudioPlayer()
        logger.debug("Voice library and audio player initialized")
        
        # Create UI
        logger.debug("Creating UI components...")
        self._create_menu()
        self._create_tabs()
        
        # Show model download confirmation
        logger.info("Scheduling model download confirmation...")
        self.after(100, self._show_model_download_confirmation)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("Application initialized")
    
    def _create_menu(self) -> None:
        """Create menu bar (simplified for cross-platform)."""
        # Note: CustomTkinter doesn't have native menu bar support
        # Using a frame with buttons instead
        menu_frame = ctk.CTkFrame(self, height=40)
        menu_frame.pack(fill="x", padx=5, pady=5)
        
        # File menu buttons
        file_label = ctk.CTkLabel(menu_frame, text="File:", font=("Arial", 12, "bold"))
        file_label.pack(side="left", padx=5)
        
        open_workspace_btn = ctk.CTkButton(
            menu_frame,
            text="Open Working Directory",
            command=self._open_workspace_folder,
            width=180
        )
        open_workspace_btn.pack(side="left", padx=5)
        
        # Help menu buttons
        help_label = ctk.CTkLabel(menu_frame, text="Help:", font=("Arial", 12, "bold"))
        help_label.pack(side="right", padx=20)
        
        about_btn = ctk.CTkButton(
            menu_frame,
            text="About",
            command=self._show_about,
            width=80
        )
        about_btn.pack(side="right", padx=5)
    
    def _create_tabs(self) -> None:
        """Create tabbed interface."""
        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add tabs
        self.tabview.add("Voice Creation")
        self.tabview.add("Narration")
        self.tabview.add("Voice Model Library")
        self.tabview.add("Settings")
        
        # Create tab content (will be initialized after models load)
        self.voice_creation_tab = None
        self.narration_tab = None
        self.saved_voices_tab = None
        self.settings_tab = None
    
    def _init_tabs(self) -> None:
        """Initialize tab content after models are loaded."""
        try:
            # Voice Model Library tab (create first so we can refresh it)
            self.saved_voices_tab = SavedVoicesTab(
                self.tabview.tab("Voice Model Library"),
                self.voice_library,
                self.config,
                workspace_mgr=self.workspace_mgr
            )
            
            # Narration tab (create second to get refresh callback)
            self.narration_tab = NarrationTab(
                self.tabview.tab("Narration"),
                self.tts_engine,
                self.voice_library,
                self.config,
                workspace_mgr=self.workspace_mgr
            )
            
            # Voice Creation tab (unified clone and design with refresh callbacks)
            self.voice_creation_tab = VoiceCreationTab(
                self.tabview.tab("Voice Creation"),
                self.tts_engine,
                self.voice_library,
                self.config,
                narration_refresh_callback=self.narration_tab.refresh_voice_list,
                saved_voices_refresh_callback=self.saved_voices_tab.refresh,
                workspace_mgr=self.workspace_mgr
            )
            
            # Settings tab
            self.settings_tab = SettingsTab(
                self.tabview.tab("Settings"),
                self.tts_engine,
                self.config,
                self._reload_models,
                workspace_mgr=self.workspace_mgr
            )
            
            logger.info("Tabs initialized")
            
        except Exception as e:
            logger.error(f"Error initializing tabs: {e}")
            messagebox.showerror("Error", f"Failed to initialize interface: {e}")
    
    def _show_model_download_confirmation(self) -> None:
        """Show confirmation dialog before downloading models."""
        model_size = self.config.get("model_size", "1.7B")
        device = self.config.get("device", "cuda:0")
        
        # Models are cached in default HuggingFace cache (not workspace)
        from pathlib import Path
        import os
        cache_dir = Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface')) / "hub"
        
        # Check if model is likely already downloaded
        model_key = f"custom_voice_{model_size}"
        from core.tts_engine import TTSEngine
        model_repo = TTSEngine.MODELS.get(model_key, "")
        
        # Simple heuristic: if cache directory exists and has substantial content, model may be cached
        model_likely_cached = False
        if cache_dir.exists():
            # Check for model-specific directory patterns
            cache_contents = list(cache_dir.glob("models--*Qwen*TTS*"))
            if cache_contents:
                model_likely_cached = True
                logger.info(f"Model appears to be cached in {cache_dir}")
        
        # If model is likely cached, skip confirmation and load directly
        if model_likely_cached:
            logger.info("Model cache detected, loading models without confirmation")
            self._load_models()
            return
        
        # First-time download - show confirmation
        # Models go to system cache, not workspace
        storage_location = str(cache_dir.parent)
        
        # Estimate download size
        if model_size == "1.7B":
            download_size = "~7 GB"
        elif model_size == "0.6B":
            download_size = "~3 GB"
        else:
            download_size = "~7 GB"
        
        message = (
            f"🚀 First-Time Model Download\n\n"
            f"Qwen-semble needs to download the Qwen3-TTS AI model:\n\n"
            f"• Model: Qwen3-TTS-{model_size}-CustomVoice\n"
            f"• Size: {download_size}\n"
            f"• Device: {device}\n"
            f"• Storage: {storage_location}\n\n"
            f"Requirements:\n"
            f"✓ Active internet connection\n"
            f"✓ Sufficient disk space\n\n"
            f"This is a one-time download. The model will be cached for future use.\n\n"
            f"Download now?"
        )
        
        response = messagebox.askyesno(
            "Model Download Required",
            message,
            icon='question'
        )
        
        if response:
            logger.info("User confirmed model download")
            self._load_models()
        else:
            logger.info("User declined model download")
            messagebox.showinfo(
                "Models Not Loaded",
                "Models were not downloaded.\n\n"
                "The application interface is available, but TTS features will not work "
                "until models are loaded.\n\n"
                "You can load models later from the Settings tab by clicking "
                "'Reload Models'."
            )
            # Initialize engine without loading models (for settings access)
            self.tts_engine = TTSEngine(
                device=self.config.get("device", "cuda:0"),
                workspace_dir=self.workspace_mgr.get_working_directory()
            )
            self._init_tabs()
    
    def _load_models(self) -> None:
        """Load TTS models in background."""
        loading_dialog = LoadingOverlay(
            self,
            title="Loading Models",
            message="Loading Qwen3-TTS models, please wait..."
        )
        
        def load_task():
            """Background task to load models."""
            try:
                logger.info("Starting model loading task...")
                # Initialize TTS engine
                device = self.config.get("device", "cuda:0")
                use_flash_attention = self.config.get("use_flash_attention", True)
                model_size = self.config.get("model_size", "1.7B")
                
                logger.info(f"Initializing TTS engine: device={device}, model_size={model_size}, flash_attn={use_flash_attention}")
                logger.debug("Creating TTSEngine instance...")
                
                self.tts_engine = TTSEngine(
                    device=device,
                    dtype="bfloat16",
                    use_flash_attention=use_flash_attention,
                    workspace_dir=self.workspace_mgr.get_working_directory()
                )
                logger.debug("TTSEngine instance created")
                
                # Load primary model (CustomVoice)
                logger.info("Loading CustomVoice model...")
                loading_dialog.update_progress(30, "Loading CustomVoice model...")
                self.tts_engine.load_custom_voice_model(
                    model_size=model_size,
                    progress_callback=lambda p, m: loading_dialog.update_progress(30 + p * 0.7, m)
                )
                
                logger.info("Model loading completed successfully")
                loading_dialog.update_progress(100, "Models loaded successfully!")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to load models: {e}")
                return e
        
        def on_complete(result):
            """Called when model loading completes."""
            logger.debug("Model loading task completed, closing loading dialog")
            loading_dialog.close()
            
            if isinstance(result, Exception):
                logger.error(f"Model loading failed with error: {result}")
                messagebox.showerror(
                    "Model Loading Failed",
                    f"Failed to load TTS models:\n\n{str(result)}\n\n"
                    "The application will continue, but TTS features will not work.\n"
                    "Check Settings to configure device and model."
                )
                # Initialize engine in CPU mode as fallback
                logger.info("Initializing fallback TTS engine in CPU mode")
                self.tts_engine = TTSEngine(device="cpu", workspace_dir=self.workspace_mgr.get_working_directory())
            else:
                logger.info("Model loading successful, proceeding with tab initialization")
            
            # Initialize tabs
            logger.debug("Starting tab initialization...")
            self._init_tabs()
        
        def on_error(error):
            """Called if model loading fails."""
            loading_dialog.close()
            messagebox.showerror("Error", f"Failed to load models: {error}")
            # Initialize with CPU fallback
            self.tts_engine = TTSEngine(device="cpu", workspace_dir=self.workspace_mgr.get_working_directory())
            self._init_tabs()
        
        # Run loading in background thread
        run_in_thread(
            self,
            load_task,
            on_success=on_complete,
            on_error=on_error
        )
    
    def _reload_models(self) -> None:
        """Reload models with new settings."""
        model_size = self.config.get("model_size", "1.7B")
        
        message = (
            "This will unload current models and reload with new settings.\n"
            "Any unsaved work will be lost.\n\n"
        )
        
        # Check if model size changed - may require download
        if self.tts_engine and hasattr(self.tts_engine, 'custom_voice_model'):
            message += (
                "Note: If you changed the model size, a new download may be required.\n\n"
            )
        
        message += "Continue?"
        
        response = messagebox.askyesno(
            "Reload Models",
            message
        )
        
        if response:
            # Unload current models
            if self.tts_engine:
                self.tts_engine.unload_all_models()
            
            # Reload (this will check cache and load or download as needed)
            self._load_models()
    
    def _open_workspace_folder(self) -> None:
        """Open working directory in file explorer."""
        workspace_path = self.workspace_mgr.get_working_directory().absolute()
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(workspace_path)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                subprocess.Popen(['xdg-open', str(workspace_path)])
        except Exception as e:
            logger.error(f"Failed to open working directory: {e}")
            messagebox.showerror("Error", f"Failed to open folder: {e}")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        about_text = (
            "Qwen-semble - TTS Voice Studio\n\n"
            "Version 1.0.0\n\n"
            "A powerful voice cloning and narration application\n"
            "powered by Qwen3-TTS models.\n\n"
            "Features:\n"
            "• Clone voices from audio samples\n"
            "• Design custom voices from descriptions\n"
            "• Multi-voice transcript narration\n"
            "• Voice library management\n\n"
            "© 2026 - Licensed under MIT"
        )
        messagebox.showinfo("About", about_text)
    
    def _on_closing(self) -> None:
        """Handle window close event."""
        # Save window size
        self.config.set("window_width", self.winfo_width(), save=False)
        self.config.set("window_height", self.winfo_height(), save=False)
        self.config.save()
        
        # Stop audio playback
        self.audio_player.stop()
        
        # Unload models
        if self.tts_engine:
            self.tts_engine.unload_all_models()
        
        logger.info("Application closing")
        self.destroy()


def run(workspace_mgr: 'WorkspaceManager'):
    """Run the application.
    
    Args:
        workspace_mgr: WorkspaceManager instance
    """
    app = QwenTTSApp(workspace_mgr)
    app.mainloop()
