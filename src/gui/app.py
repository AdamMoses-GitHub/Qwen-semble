"""Main application window with tabbed interface."""

import customtkinter as ctk
from tkinter import messagebox
import os
import webbrowser
from pathlib import Path
from typing import Optional, Dict, List, TYPE_CHECKING

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


class AboutDialog(ctk.CTkToplevel):
    """Elegant About dialog window."""
    
    def __init__(self, parent):
        """Initialize About dialog.
        
        Args:
            parent: Parent window
        """
        super().__init__(parent)
        
        self.title("About Qwen-semble")
        self.geometry("600x650")
        self.resizable(False, False)
        
        # Center window on parent
        self.transient(parent)
        self.grab_set()
        
        # Create UI
        self._create_ui()
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (650 // 2)
        self.geometry(f"600x650+{x}+{y}")
    
    def _create_ui(self) -> None:
        """Create dialog UI."""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header section with app name
        header_frame = ctk.CTkFrame(main_frame, fg_color=("gray85", "gray20"))
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Qwen-semble",
            font=("Arial", 32, "bold")
        )
        title_label.pack(pady=(15, 5))
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="TTS Voice Studio",
            font=("Arial", 16),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 15))
        
        # Version
        version_label = ctk.CTkLabel(
            main_frame,
            text="Version 1.0.0",
            font=("Arial", 12, "bold")
        )
        version_label.pack(pady=(0, 10))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="A powerful voice cloning and narration application\\npowered by Qwen3-TTS models.",
            font=("Arial", 11),
            justify="center"
        )
        desc_label.pack(pady=(0, 20))
        
        # Features section
        features_frame = ctk.CTkFrame(main_frame)
        features_frame.pack(fill="x", pady=(0, 15))
        
        features_title = ctk.CTkLabel(
            features_frame,
            text="Features",
            font=("Arial", 14, "bold")
        )
        features_title.pack(pady=(10, 8))
        
        features_text = (
            "🎙️  Clone voices from audio samples\\n"
            "🎨  Design custom voices from descriptions\\n"
            "📖  Multi-voice transcript narration\\n"
            "💾  Voice library management\\n"
            "🚀  GPU acceleration with CUDA support\\n"
            "🌍  Multilingual (11 languages)\\n"
            "💻  100% local processing"
        )
        
        features_label = ctk.CTkLabel(
            features_frame,
            text=features_text,
            font=("Arial", 11),
            justify="left"
        )
        features_label.pack(pady=(0, 10), padx=20)
        
        # GitHub link section
        github_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray15"))
        github_frame.pack(fill="x", pady=(0, 15))
        
        github_label = ctk.CTkLabel(
            github_frame,
            text="GitHub Repository",
            font=("Arial", 12, "bold")
        )
        github_label.pack(pady=(10, 5))
        
        github_url = "https://github.com/AdamMoses-GitHub/Qwen-semble"
        github_link = ctk.CTkButton(
            github_frame,
            text=github_url,
            font=("Arial", 10),
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color=("blue", "lightblue"),
            cursor="hand2",
            command=lambda: webbrowser.open(github_url)
        )
        github_link.pack(pady=(0, 10))
        
        # Copyright
        copyright_label = ctk.CTkLabel(
            main_frame,
            text="© 2026 - Licensed under MIT",
            font=("Arial", 10),
            text_color="gray"
        )
        copyright_label.pack(pady=(5, 15))
        
        # Close button
        close_btn = ctk.CTkButton(
            main_frame,
            text="Close",
            command=self.destroy,
            width=120,
            height=32
        )
        close_btn.pack(pady=(0, 0))


class QwenTTSApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self, workspace_mgr: 'WorkspaceManager', model_selection: Optional[Dict] = None):
        """Initialize main application.
        
        Args:
            workspace_mgr: WorkspaceManager instance
            model_selection: Optional dict from model selection dialog (for first launch)
        """
        super().__init__()
        
        self.workspace_mgr = workspace_mgr
        self.model_selection = model_selection  # Store for model loading
        
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
        
        # Handle model loading
        logger.info("Scheduling model initialization...")
        self.after(100, self._initialize_models)
        
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
    
    def _initialize_models(self) -> None:
        """Initialize models based on first launch or existing configuration."""
        # Check if this is first launch (model_selection provided)
        if self.model_selection is not None:
            logger.info("First launch - using model selection from dialog")
            
            if self.model_selection["skip"]:
                # User chose to skip model download
                logger.info("User chose to skip model download")
                self._init_without_models()
                return
            
            # Models were selected, download and load them
            models_to_download = self.model_selection["models"]
            active_model = self.model_selection["active_model"]
            
            logger.info(f"Downloading models: {models_to_download}, active: {active_model}")
            self._download_and_load_models(models_to_download, active_model)
        
        else:
            # Not first launch - check config for downloaded models
            logger.info("Not first launch - checking config for models")
            
            downloaded_models = self.config.get("downloaded_models", [])
            active_model = self.config.get("active_model", None)
            
            if not downloaded_models or active_model is None:
                # No models downloaded
                logger.info("No models found in config")
                self._init_without_models()
                return
            
            # Load the active model
            logger.info(f"Loading active model: {active_model}")
            self._load_models(active_model)
    
    def _init_without_models(self) -> None:
        """Initialize application without loading any models."""
        logger.info("Initializing application without models")
        
        # Create TTS engine instance without loading models
        self.tts_engine = TTSEngine(
            device=self.config.get("device", "cuda:0"),
            workspace_dir=self.workspace_mgr.get_working_directory()
        )
        
        # Initialize tabs
        self._init_tabs()
        
        # Show warning banner
        self._show_no_model_warning()
    
    def _show_no_model_warning(self) -> None:
        """Show warning banner when no model is loaded."""
        warning_frame = ctk.CTkFrame(self, fg_color="orange", height=50)
        warning_frame.pack(fill="x", padx=5, pady=(5, 0), before=self.tabview)
        warning_frame.pack_propagate(False)
        
        warning_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ No AI model loaded. TTS features are disabled.",
            font=("Arial", 14, "bold"),
            text_color="black"
        )
        warning_label.pack(side="left", padx=20, pady=10)
        
        download_btn = ctk.CTkButton(
            warning_frame,
            text="Download Models",
            command=self._show_model_download_dialog,
            fg_color="darkgreen",
            hover_color="green",
            font=("Arial", 12, "bold")
        )
        download_btn.pack(side="right", padx=20, pady=10)
        
        self.warning_banner = warning_frame
    
    def _show_model_download_dialog(self) -> None:
        """Show model selection dialog to download models."""
        from gui.model_selection_dialog import show_model_selection_dialog
        
        model_selection = show_model_selection_dialog()
        
        if model_selection and not model_selection["skip"]:
            models_to_download = model_selection["models"]
            active_model = model_selection["active_model"]
            
            # Update config
            self.config.set("downloaded_models", models_to_download, save=False)
            self.config.set("active_model", active_model, save=False)
            self.config.set("device", model_selection["device"], save=True)
            
            # Remove warning banner
            if hasattr(self, 'warning_banner'):
                self.warning_banner.destroy()
                delattr(self, 'warning_banner')
            
            # Download and load models
            self._download_and_load_models(models_to_download, active_model)
    
    def _download_and_load_models(self, models_to_download: List[str], active_model: str) -> None:
        """Download (if needed) and load selected models.
        
        Args:
            models_to_download: List of model sizes to download ["1.7B", "0.6B"]
            active_model: Which model to load as active ("1.7B" or "0.6B")
        """
        logger.info(f"Starting model download/load: {models_to_download}, active: {active_model}")
        
        loading_dialog = LoadingOverlay(
            self,
            title="Downloading Models",
            message="Preparing to download models..."
        )
        
        def download_task():
            """Background task to download and load models."""
            try:
                # Initialize TTS engine
                device = self.config.get("device", "cuda:0")
                use_flash_attention = self.config.get("use_flash_attention", False)
                
                logger.info(f"Initializing TTS engine: device={device}")
                
                self.tts_engine = TTSEngine(
                    device=device,
                    dtype="bfloat16",
                    use_flash_attention=use_flash_attention,
                    workspace_dir=self.workspace_mgr.get_working_directory()
                )
                
                total_models = len(models_to_download)
                
                # Download each model
                for idx, model_size in enumerate(models_to_download, 1):
                    logger.info(f"Downloading model {idx}/{total_models}: {model_size}")
                    loading_dialog.update_progress(
                        0,
                        f"Downloading model {idx}/{total_models}: Qwen3-TTS-{model_size}..."
                    )
                    
                    # Load the model (will download if needed)
                    self.tts_engine.load_custom_voice_model(
                        model_size=model_size,
                        progress_callback=lambda p, m: loading_dialog.update_progress(
                            ((idx - 1) / total_models + p / total_models) * 100,
                            f"Model {idx}/{total_models}: {m}"
                        )
                    )
                    
                    # Unload if not the active model (save memory)
                    if model_size != active_model:
                        logger.info(f"Unloading {model_size} (not active model)")
                        self.tts_engine.unload_all_models()
                
                # Load active model if it's not the last one downloaded
                if active_model != models_to_download[-1]:
                    logger.info(f"Loading active model: {active_model}")
                    loading_dialog.update_progress(95, f"Loading active model: {active_model}...")
                    self.tts_engine.load_custom_voice_model(model_size=active_model)
                
                loading_dialog.update_progress(100, "Models ready!")
                logger.info("All models downloaded successfully")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to download/load models: {e}", exc_info=True)
                return e
        
        def on_complete(result):
            """Called when download completes."""
            loading_dialog.close()
            
            if isinstance(result, Exception):
                logger.error(f"Model download failed: {result}")
                messagebox.showerror(
                    "Download Failed",
                    f"Failed to download models:\n\n{str(result)}\n\n"
                    "Check your internet connection and try again."
                )
                self._init_without_models()
            else:
                logger.info("Models downloaded and loaded successfully")
                # Initialize tabs if not already done
                if not self.voice_creation_tab:
                    self._init_tabs()
        
        def on_error(error):
            """Called if download fails."""
            loading_dialog.close()
            messagebox.showerror("Error", f"Failed to download models: {error}")
            self._init_without_models()
        
        # Run in background thread
        run_in_thread(
            self,
            download_task,
            on_success=on_complete,
            on_error=on_error
        )
    
    def _load_models(self, model_size: str) -> None:
        """Load TTS model in background.
        
        Args:
            model_size: Model size to load ("1.7B" or "0.6B")
        """
        loading_dialog = LoadingOverlay(
            self,
            title="Loading Model",
            message=f"Loading Qwen3-TTS-{model_size} model..."
        )
        
        def load_task():
            """Background task to load model."""
            try:
                logger.info(f"Starting model loading: {model_size}")
                
                # Initialize TTS engine if not already done
                if not self.tts_engine:
                    device = self.config.get("device", "cuda:0")
                    use_flash_attention = self.config.get("use_flash_attention", False)
                    
                    self.tts_engine = TTSEngine(
                        device=device,
                        dtype="bfloat16",
                        use_flash_attention=use_flash_attention,
                        workspace_dir=self.workspace_mgr.get_working_directory()
                    )
                
                # Load the model
                self.tts_engine.load_custom_voice_model(
                    model_size=model_size,
                    progress_callback=lambda p, m: loading_dialog.update_progress(p * 100, m)
                )
                
                logger.info(f"Model {model_size} loaded successfully")
                loading_dialog.update_progress(100, "Model loaded!")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}", exc_info=True)
                return e
        
        def on_complete(result):
            """Called when model loading completes."""
            loading_dialog.close()
            
            if isinstance(result, Exception):
                logger.error(f"Model loading failed: {result}")
                messagebox.showerror(
                    "Loading Failed",
                    f"Failed to load model:\n\n{str(result)}\n\n"
                    "Continuing without models."
                )
                self._init_without_models()
            else:
                logger.info("Model loaded successfully")
                # Initialize tabs if not already done
                if not self.voice_creation_tab:
                    self._init_tabs()
        
        def on_error(error):
            """Called if loading fails."""
            loading_dialog.close()
            messagebox.showerror("Error", f"Failed to load model: {error}")
            self._init_without_models()
        
        # Run in background thread
        run_in_thread(
            self,
            load_task,
            on_success=on_complete,
            on_error=on_error
        )
    
    def _reload_models(self) -> None:
        """Reload models with new settings."""
        active_model = self.config.get("active_model", "1.7B")
        
        message = (
            "This will unload current models and reload with new settings.\n"
            "Any unsaved work will be lost.\n\n"
            "Continue?"
        )
        
        response = messagebox.askyesno(
            "Reload Models",
            message
        )
        
        if response:
            # Unload current models
            if self.tts_engine:
                self.tts_engine.unload_all_models()
            
            # Reload the active model
            if active_model:
                self._load_models(active_model)
            else:
                # No model configured, show download dialog
                self._show_model_download_dialog()
    
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
        AboutDialog(self)
    
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


def run(workspace_mgr: 'WorkspaceManager', model_selection: Optional[Dict] = None):
    """Run the application.
    
    Args:
        workspace_mgr: WorkspaceManager instance
        model_selection: Optional dict from model selection dialog (for first launch)
    """
    app = QwenTTSApp(workspace_mgr, model_selection)
    app.mainloop()
