"""Main application window with tabbed interface."""

import customtkinter as ctk
from tkinter import messagebox
import os
from pathlib import Path

from core.tts_engine import TTSEngine
from core.voice_library import VoiceLibrary
from core.audio_utils import AudioPlayer
from utils.config import Config
from utils.error_handler import logger, ensure_directory
from utils.threading_helpers import run_in_thread

from gui.tab_voice_clone import VoiceCloneTab
from gui.tab_voice_design import VoiceDesignTab
from gui.tab_narration import NarrationTab
from gui.tab_settings import SettingsTab
from gui.components import LoadingOverlay


class QwenTTSApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        """Initialize main application."""
        super().__init__()
        
        # Configure window
        self.title("Qwen-semble - TTS Voice Studio")
        
        # Load configuration
        self.config = Config()
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
        self.voice_library = VoiceLibrary()
        self.audio_player = AudioPlayer()
        logger.debug("Voice library and audio player initialized")
        
        # Ensure output directories exist
        logger.debug("Ensuring output directories exist...")
        self._ensure_directories()
        
        # Create UI
        logger.debug("Creating UI components...")
        self._create_menu()
        self._create_tabs()
        
        # Load models in background
        logger.info("Scheduling model loading...")
        self.after(100, self._load_models)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("Application initialized")
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        logger.debug("Checking/creating required directories...")
        directories = [
            "output",
            "output/cloned_voices",
            "output/designed_voices",
            "output/narrations",
            "output/temp",
            "output/logs",
            "config"
        ]
        for directory in directories:
            ensure_directory(directory)
        logger.debug(f"Created/verified {len(directories)} directories")
    
    def _create_menu(self) -> None:
        """Create menu bar (simplified for cross-platform)."""
        # Note: CustomTkinter doesn't have native menu bar support
        # Using a frame with buttons instead
        menu_frame = ctk.CTkFrame(self, height=40)
        menu_frame.pack(fill="x", padx=5, pady=5)
        
        # File menu buttons
        file_label = ctk.CTkLabel(menu_frame, text="File:", font=("Arial", 12, "bold"))
        file_label.pack(side="left", padx=5)
        
        open_output_btn = ctk.CTkButton(
            menu_frame,
            text="Open Output Folder",
            command=self._open_output_folder,
            width=150
        )
        open_output_btn.pack(side="left", padx=5)
        
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
        self.tabview.add("Voice Clone")
        self.tabview.add("Voice Design")
        self.tabview.add("Narration")
        self.tabview.add("Settings")
        
        # Create tab content (will be initialized after models load)
        self.voice_clone_tab = None
        self.voice_design_tab = None
        self.narration_tab = None
        self.settings_tab = None
    
    def _init_tabs(self) -> None:
        """Initialize tab content after models are loaded."""
        try:
            # Narration tab (create first to get refresh callback)
            self.narration_tab = NarrationTab(
                self.tabview.tab("Narration"),
                self.tts_engine,
                self.voice_library,
                self.config
            )
            
            # Voice Clone tab (with narration refresh callback)
            self.voice_clone_tab = VoiceCloneTab(
                self.tabview.tab("Voice Clone"),
                self.tts_engine,
                self.voice_library,
                self.config,
                narration_refresh_callback=self.narration_tab.refresh_voice_list
            )
            
            # Voice Design tab (with narration refresh callback)
            self.voice_design_tab = VoiceDesignTab(
                self.tabview.tab("Voice Design"),
                self.tts_engine,
                self.voice_library,
                self.config,
                narration_refresh_callback=self.narration_tab.refresh_voice_list
            )
            
            # Settings tab
            self.settings_tab = SettingsTab(
                self.tabview.tab("Settings"),
                self.tts_engine,
                self.config,
                self._reload_models
            )
            
            logger.info("Tabs initialized")
            
        except Exception as e:
            logger.error(f"Error initializing tabs: {e}")
            messagebox.showerror("Error", f"Failed to initialize interface: {e}")
    
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
                    use_flash_attention=use_flash_attention
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
                self.tts_engine = TTSEngine(device="cpu")
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
            self.tts_engine = TTSEngine(device="cpu")
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
        response = messagebox.askyesno(
            "Reload Models",
            "This will unload current models and reload with new settings.\n"
            "Any unsaved work will be lost. Continue?"
        )
        
        if response:
            # Unload current models
            if self.tts_engine:
                self.tts_engine.unload_all_models()
            
            # Reload
            self._load_models()
    
    def _open_output_folder(self) -> None:
        """Open output folder in file explorer."""
        output_dir = Path(self.config.get("output_dir", "output")).absolute()
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                subprocess.Popen(['xdg-open', str(output_dir)])
        except Exception as e:
            logger.error(f"Failed to open output folder: {e}")
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


def run():
    """Run the application."""
    app = QwenTTSApp()
    app.mainloop()
