"""Settings tab interface."""

from typing import TYPE_CHECKING, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from utils.error_handler import logger
from utils.theme import get_theme_colors

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager


class SettingsTab(ctk.CTkFrame):
    """Application settings tab."""
    
    def __init__(self, parent, tts_engine, config, reload_callback, workspace_mgr: Optional['WorkspaceManager'] = None, download_callback=None):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.config = config
        self.reload_callback = reload_callback
        self.workspace_mgr = workspace_mgr
        self.download_callback = download_callback
        
        # Track UI elements for dynamic updates
        self.help_banner = None
        self.model_section_parent = None
        self.model_status_frame = None
        self.active_model_frame = None
        self.active_model_combo = None
        self.active_model_var = None
        self.loaded_models_frame = None
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create settings UI."""
        # Main scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Model Configuration
        self._create_model_section(scroll_frame)
        
        # HuggingFace Authentication
        self._create_auth_section(scroll_frame)
        
        # Output Directories
        self._create_dirs_section(scroll_frame)
        
        # Interface Options
        self._create_interface_section(scroll_frame)
        
        # Advanced Settings
        self._create_advanced_section(scroll_frame)
        
        # Action Buttons
        self._create_actions_section(scroll_frame)
    
    def _create_model_section(self, parent) -> None:
        """Create model configuration section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        # Store reference for refreshing
        self.model_section_parent = section
        
        title = ctk.CTkLabel(section, text="Model Configuration", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Check if no models installed and show help text
        downloaded_models = self.config.get("downloaded_models", [])
        if not downloaded_models:
            self._create_no_models_help(section)
        
        # Device selection
        device_frame = ctk.CTkFrame(section)
        device_frame.pack(fill="x", padx=10, pady=5)
        
        device_label = ctk.CTkLabel(device_frame, text="Compute Device:", width=150)
        device_label.pack(side="left", padx=5)
        
        # Get available devices
        devices = self.tts_engine.get_available_devices()
        device_options = []
        for device in devices:
            device_str = f"{device['id']} - {device['name']} ({device['memory']})"
            device_options.append(device_str)
        
        current_device = self.config.get("device", "cuda:0")
        self.device_combo = ctk.CTkComboBox(device_frame, values=device_options, width=300)
        
        # Set current device
        for i, device in enumerate(devices):
            if device['id'] == current_device:
                self.device_combo.set(device_options[i])
                break
        
        self.device_combo.pack(side="left", padx=5)
        
        # Installed Models Status Display
        status_frame = ctk.CTkFrame(section)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        status_label = ctk.CTkLabel(status_frame, text="Installed Models:", width=150, anchor="w")
        status_label.pack(side="left", padx=5, anchor="w")
        
        # Get downloaded models
        downloaded_models = self.config.get("downloaded_models", [])
        
        # Status text frame
        status_text_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_text_frame.pack(side="left", fill="x", expand=True, padx=10)
        
        # Store reference for refresh
        self.model_status_frame = status_text_frame
        
        # Create status labels
        self._create_model_status_labels(status_text_frame, downloaded_models)
        
        # Manage Models button
        manage_models_btn = ctk.CTkButton(
            status_frame,
            text="📥 Manage Models",
            command=self._manage_models,
            width=140,
            height=32,
            fg_color="#1f6aa5",
            hover_color="#144870"
        )
        manage_models_btn.pack(side="right", padx=10)
        
        # Active Model Switcher (always visible)
        self._create_active_model_switcher(section)
        
        # FlashAttention
        flash_frame = ctk.CTkFrame(section)
        flash_frame.pack(fill="x", padx=10, pady=5)
        
        self.flash_var = ctk.BooleanVar(value=self.config.get("use_flash_attention", True))
        flash_check = ctk.CTkCheckBox(
            flash_frame,
            text="Use FlashAttention 2 (recommended for GPU, requires compatible hardware)",
            variable=self.flash_var
        )
        flash_check.pack(side="left", padx=5)

        # Loaded models / VRAM management
        self._create_loaded_models_section(section)
    
    def _create_model_status_labels(self, parent, downloaded_models: list) -> None:
        """Create status labels for installed models.
        
        Args:
            parent: Parent widget
            downloaded_models: List of downloaded model sizes
        """
        # 1.7B Model Status
        is_1_7b_installed = "1.7B" in downloaded_models
        
        # Create row frame for 1.7B
        row_1_7b = ctk.CTkFrame(parent, fg_color="transparent")
        row_1_7b.pack(fill="x", pady=3)
        
        # Model name label
        name_1_7b = ctk.CTkLabel(
            row_1_7b,
            text="• 1.7B (higher quality, ~7GB VRAM)",
            font=("Arial", 12),
            anchor="w"
        )
        name_1_7b.pack(side="left", padx=(0, 10))
        
        # Status badge with background
        if is_1_7b_installed:
            status_bg = "#16a34a"  # Green background
            status_text = "✓ Installed"
        else:
            status_bg = "#ea580c"  # Orange background
            status_text = "⚠ Not Installed"
        
        status_1_7b = ctk.CTkLabel(
            row_1_7b,
            text=status_text,
            font=("Arial", 13, "bold"),
            text_color="white",
            fg_color=status_bg,
            corner_radius=6,
            padx=12,
            pady=4
        )
        status_1_7b.pack(side="left")
        
        # 0.6B Model Status
        is_0_6b_installed = "0.6B" in downloaded_models
        
        # Create row frame for 0.6B
        row_0_6b = ctk.CTkFrame(parent, fg_color="transparent")
        row_0_6b.pack(fill="x", pady=3)
        
        # Model name label
        name_0_6b = ctk.CTkLabel(
            row_0_6b,
            text="• 0.6B (faster, ~2.5GB VRAM)",
            font=("Arial", 12),
            anchor="w"
        )
        name_0_6b.pack(side="left", padx=(0, 10))
        
        # Status badge with background
        if is_0_6b_installed:
            status_bg = "#16a34a"  # Green background
            status_text = "✓ Installed"
        else:
            status_bg = "#ea580c"  # Orange background
            status_text = "⚠ Not Installed"
        
        status_0_6b = ctk.CTkLabel(
            row_0_6b,
            text=status_text,
            font=("Arial", 13, "bold"),
            text_color="white",
            fg_color=status_bg,
            corner_radius=6,
            padx=12,
            pady=4
        )
        status_0_6b.pack(side="left")
    
    def _create_loaded_models_section(self, parent) -> None:
        """Create collapsible section showing which models are in memory."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=(5, 10))
        self.loaded_models_frame = frame
        self._refresh_loaded_models_section()

    def _refresh_loaded_models_section(self) -> None:
        """Rebuild the loaded-models display from current engine state."""
        if not self.loaded_models_frame or not self.loaded_models_frame.winfo_exists():
            return

        for w in self.loaded_models_frame.winfo_children():
            w.destroy()

        colors = get_theme_colors()

        # Header row
        header_row = ctk.CTkFrame(self.loaded_models_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=5, pady=(8, 4))

        ctk.CTkLabel(
            header_row,
            text="Loaded Models (Memory Management)",
            font=("Arial", 12, "bold")
        ).pack(side="left")

        # VRAM / RAM usage badge
        try:
            import torch
            if "cuda" in self.tts_engine.device and torch.cuda.is_available():
                alloc = torch.cuda.memory_allocated() / 1024 ** 3
                total = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
                mem_text = f"VRAM: {alloc:.1f} / {total:.1f} GB used"
                mem_color = colors["error_text"] if alloc / total > 0.85 else colors["text_secondary"]
            else:
                mem_text = "CPU mode (system RAM)"
                mem_color = colors["text_secondary"]
        except Exception:
            mem_text = ""
            mem_color = colors["text_secondary"]

        ctk.CTkLabel(
            header_row,
            text=mem_text,
            font=("Arial", 10),
            text_color=mem_color
        ).pack(side="right", padx=5)

        # Per-model rows
        model_defs = [
            ("custom_voice", "CustomVoice",   self.tts_engine.custom_voice_model),
            ("voice_design", "VoiceDesign",    self.tts_engine.voice_design_model),
            ("base",          "Base",           self.tts_engine.base_model),
        ]
        any_loaded = False
        for model_key, model_label, model_instance in model_defs:
            row = ctk.CTkFrame(self.loaded_models_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            if model_instance is not None:
                status_text  = "● Loaded"
                status_color = colors["success_text"]
                btn_state    = "normal"
                any_loaded   = True
            else:
                status_text  = "○ Not loaded"
                status_color = colors["text_secondary"]
                btn_state    = "disabled"

            ctk.CTkLabel(
                row,
                text=f"  {model_label}:",
                font=("Arial", 12),
                width=120,
                anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=status_text,
                font=("Arial", 12, "bold"),
                text_color=status_color
            ).pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                row,
                text="Unload",
                width=80,
                height=26,
                state=btn_state,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda mk=model_key, ml=model_label: self._unload_model(mk, ml)
            ).pack(side="right", padx=5)

        # Unload-all button
        bottom = ctk.CTkFrame(self.loaded_models_frame, fg_color="transparent")
        bottom.pack(fill="x", padx=5, pady=(4, 8))
        ctk.CTkButton(
            bottom,
            text="Unload All Models",
            width=160,
            height=30,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            state="normal" if any_loaded else "disabled",
            command=self._unload_all_models
        ).pack(side="right", padx=5)

        ctk.CTkLabel(
            bottom,
            text="Free VRAM without restarting the app",
            font=("Arial", 10),
            text_color=colors["text_secondary"]
        ).pack(side="left", padx=5)

    def _unload_model(self, model_key: str, model_label: str) -> None:
        """Unload a specific model to free memory."""
        if not messagebox.askyesno(
            "Unload Model",
            f"Unload {model_label} model?\n\n"
            "This frees VRAM/RAM. The model will be reloaded automatically next time it is needed.\n\nContinue?"
        ):
            return
        self.tts_engine.unload_model(model_key)
        logger.info(f"User unloaded {model_label} model from settings")
        self._refresh_loaded_models_section()

    def _unload_all_models(self) -> None:
        """Unload all loaded models to free memory."""
        if not messagebox.askyesno(
            "Unload All Models",
            "Unload all currently loaded models?\n\n"
            "This frees all model memory. Models will reload automatically on next use.\n\nContinue?"
        ):
            return
        self.tts_engine.unload_all_models()
        logger.info("User unloaded all models from settings")
        self._refresh_loaded_models_section()

    def _create_active_model_switcher(self, parent) -> None:
        """Create active model switcher (always visible)."""
        downloaded_models = self.config.get("downloaded_models", [])
        active_model = self.config.get("active_model", None)
        
        switcher_frame = ctk.CTkFrame(parent)
        switcher_frame.pack(fill="x", padx=10, pady=10)
        
        # Store reference for refresh
        self.active_model_frame = switcher_frame
        
        switcher_label = ctk.CTkLabel(switcher_frame, text="Active Model:", width=150)
        switcher_label.pack(side="left", padx=5)
        
        # Handle different cases
        if not downloaded_models:
            # No models installed
            self.active_model_var = ctk.StringVar(value="None")
            self.active_model_combo = ctk.CTkComboBox(
                switcher_frame,
                values=["None (Click Manage Models)"],
                variable=self.active_model_var,
                width=250,
                state="disabled"
            )
        else:
            # One or more models installed
            self.active_model_var = ctk.StringVar(value=active_model or downloaded_models[0])
            self.active_model_combo = ctk.CTkComboBox(
                switcher_frame,
                values=downloaded_models,
                variable=self.active_model_var,
                width=200,
                command=self._on_active_model_changed,
                state="readonly"
            )
        
        self.active_model_combo.pack(side="left", padx=5)
        
        # Info label - only show if models are available
        if downloaded_models:
            colors = get_theme_colors()
            info_text = "\ud83d\udca1 Switch models instantly" if len(downloaded_models) > 1 else "\ud83d\udca1 Only one model installed"
            info_label = ctk.CTkLabel(
                switcher_frame,
                text=info_text,
                text_color=colors["text_secondary"],
                font=("Arial", 10)
            )
            info_label.pack(side="left", padx=10)
    
    def _create_no_models_help(self, parent) -> None:
        """Create help banner when no models are installed."""
        help_frame = ctk.CTkFrame(parent, fg_color="#f59e0b", corner_radius=8)
        help_frame.pack(fill="x", padx=10, pady=10)
        
        # Store reference for cleanup
        self.help_banner = help_frame
        
        icon_label = ctk.CTkLabel(
            help_frame,
            text="⚠️",
            font=("Arial", 24),
            text_color="white"
        )
        icon_label.pack(side="left", padx=15, pady=10)
        
        text_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, pady=10)
        
        title_label = ctk.CTkLabel(
            text_frame,
            text="No AI Models Installed",
            font=("Arial", 14, "bold"),
            text_color="white",
            anchor="w"
        )
        title_label.pack(anchor="w", padx=5)
        
        subtitle_label = ctk.CTkLabel(
            text_frame,
            text="Click '📥 Manage Models' button below to download models for voice synthesis",
            font=("Arial", 11),
            text_color="white",
            anchor="w"
        )
        subtitle_label.pack(anchor="w", padx=5)
    
    def _refresh_model_selection_ui(self) -> None:
        """Refresh the model selection UI to reflect current installation status."""
        if not self.model_section_parent:
            return
        
        logger.debug("Refreshing model selection UI")
        
        # Get current state
        downloaded_models = self.config.get("downloaded_models", [])
        active_model = self.config.get("active_model", None)
        
        # Update help banner visibility
        if not downloaded_models:
            # Show help banner if not already visible
            if not self.help_banner or not self.help_banner.winfo_exists():
                self._create_no_models_help(self.model_section_parent)
        else:
            # Remove help banner if exists
            if self.help_banner and self.help_banner.winfo_exists():
                self.help_banner.destroy()
                self.help_banner = None
        
        # Update model status display
        if self.model_status_frame and self.model_status_frame.winfo_exists():
            # Clear old status labels
            for widget in self.model_status_frame.winfo_children():
                widget.destroy()
            # Recreate with current status
            self._create_model_status_labels(self.model_status_frame, downloaded_models)
        
        # Update active model dropdown
        if self.active_model_combo and self.active_model_combo.winfo_exists():
            if not downloaded_models:
                # No models - show disabled state
                self.active_model_combo.configure(
                    values=["None (Click Manage Models)"],
                    state="disabled"
                )
                self.active_model_var.set("None")
            else:
                # Models available - update dropdown
                self.active_model_combo.configure(
                    values=downloaded_models,
                    state="readonly"
                )
                # Set to active model or first available
                if active_model and active_model in downloaded_models:
                    self.active_model_var.set(active_model)
                elif downloaded_models:
                    self.active_model_var.set(downloaded_models[0])
        
        logger.debug(f"Model selection UI refreshed: {downloaded_models}, active: {active_model}")
    
    def _on_active_model_changed(self, selected_model: str) -> None:
        """Handle active model change.
        
        Args:
            selected_model: The newly selected model size
        """
        logger.info(f"User requested model switch to: {selected_model}")
        
        response = messagebox.askyesno(
            "Switch Model",
            f"Switch to {selected_model} model?\n\n"
            "This will unload the current model and load the selected one.\n"
            "Any unsaved work will be lost.\n\n"
            "Continue?"
        )
        
        if response:
            self._switch_model(selected_model)
        else:
            # User cancelled, revert selection
            current_active = self.config.get("active_model")
            self.active_model_var.set(current_active)
    
    def _switch_model(self, new_model: str) -> None:
        """Switch to a different model.
        
        Args:
            new_model: Model size to switch to
        """
        from gui.components import LoadingOverlay
        from utils.threading_helpers import run_in_thread
        
        loading_dialog = LoadingOverlay(
            self,
            title="Switching Model",
            message=f"Switching to {new_model} model..."
        )
        
        def switch_task():
            """Background task to switch models."""
            try:
                logger.info(f"Unloading current model...")
                
                # Unload current model
                if self.tts_engine:
                    self.tts_engine.unload_all_models()
                
                logger.info(f"Loading {new_model} model...")
                loading_dialog.update_progress(30, f"Loading {new_model}...")
                
                # Load new model
                self.tts_engine.load_custom_voice_model(
                    model_size=new_model,
                    progress_callback=lambda p, m: loading_dialog.update_progress(30 + p * 0.7, m)
                )
                
                loading_dialog.update_progress(100, "Model switched!")
                logger.info(f"Successfully switched to {new_model}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to switch model: {e}", exc_info=True)
                return e
        
        def on_complete(result):
            """Called when switch completes."""
            loading_dialog.close()
            
            if isinstance(result, Exception):
                logger.error(f"Model switch failed: {result}")
                messagebox.showerror(
                    "Switch Failed",
                    f"Failed to switch model:\n\n{str(result)}"
                )
                # Revert selection
                current_active = self.config.get("active_model")
                self.active_model_var.set(current_active)
            else:
                # Update config
                self.config.set("active_model", new_model, save=True)
                messagebox.showinfo(
                    "Success",
                    f"Successfully switched to {new_model} model!"
                )
        
        def on_error(error):
            """Called if switch fails."""
            loading_dialog.close()
            messagebox.showerror("Error", f"Failed to switch model: {error}")
            # Revert selection
            current_active = self.config.get("active_model")
            self.active_model_var.set(current_active)
        
        # Run in background thread
        run_in_thread(
            self,
            switch_task,
            on_success=on_complete,
            on_error=on_error
        )
    
    def _create_auth_section(self, parent) -> None:
        """Create HuggingFace authentication section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        title = ctk.CTkLabel(section, text="HuggingFace Authentication", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        colors = get_theme_colors()
        info_label = ctk.CTkLabel(
            section,
            text="Required for downloading models. Get your token at huggingface.co/settings/tokens",
            text_color=colors["text_secondary"]
        )
        info_label.pack(pady=5)
        
        token_frame = ctk.CTkFrame(section)
        token_frame.pack(fill="x", padx=10, pady=5)
        
        token_label = ctk.CTkLabel(token_frame, text="Token:", width=100)
        token_label.pack(side="left", padx=5)
        
        self.token_entry = ctk.CTkEntry(token_frame, width=400, show="*", placeholder_text="hf_...")
        self.token_entry.pack(side="left", padx=5)
        
        # Check for existing token
        try:
            from huggingface_hub import HfFolder
            token = HfFolder.get_token()
            if token:
                self.token_entry.insert(0, token)
        except:
            pass
        
        btn_frame = ctk.CTkFrame(section)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        validate_btn = ctk.CTkButton(btn_frame, text="Validate Token", command=self._validate_token, width=120)
        validate_btn.pack(side="left", padx=5)
        
        save_token_btn = ctk.CTkButton(btn_frame, text="Save Token", command=self._save_token, width=120)
        save_token_btn.pack(side="left", padx=5)
        
        clear_token_btn = ctk.CTkButton(btn_frame, text="Clear Token", command=self._clear_token, width=120)
        clear_token_btn.pack(side="left", padx=5)
        
        self.token_status_label = ctk.CTkLabel(section, text="")
        self.token_status_label.pack(pady=5)
    
    def _create_dirs_section(self, parent) -> None:
        """Create directories section."""
        # Skip this section in workspace mode (directories managed by workspace)
        if self.workspace_mgr:
            # Show workspace info instead
            section = ctk.CTkFrame(parent)
            section.pack(fill="x", pady=10)
            
            title = ctk.CTkLabel(section, text="Workspace", font=("Arial", 14, "bold"))
            title.pack(pady=10)
            
            info_label = ctk.CTkLabel(
                section,
                text=f"Active Workspace:\n{self.workspace_mgr.get_working_directory()}",
                font=("Arial", 11),
                justify="left"
            )
            info_label.pack(padx=20, pady=10)
            
            return
        
        # Legacy mode - show output directory settings
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        title = ctk.CTkLabel(section, text="Output Directories", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Output directory
        output_frame = ctk.CTkFrame(section)
        output_frame.pack(fill="x", padx=10, pady=5)
        
        output_label = ctk.CTkLabel(output_frame, text="Output Folder:", width=120)
        output_label.pack(side="left", padx=5)
        
        self.output_entry = ctk.CTkEntry(output_frame, width=300)
        self.output_entry.insert(0, self.config.get("output_dir", "output/"))
        self.output_entry.pack(side="left", padx=5)
        
        output_browse_btn = ctk.CTkButton(
            output_frame,
            text="Browse...",
            command=lambda: self._browse_directory(self.output_entry),
            width=100
        )
        output_browse_btn.pack(side="left", padx=5)
    
    def _create_interface_section(self, parent) -> None:
        """Create interface options section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        title = ctk.CTkLabel(section, text="Interface Options", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Theme
        theme_frame = ctk.CTkFrame(section)
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        theme_label = ctk.CTkLabel(theme_frame, text="Theme:", width=120)
        theme_label.pack(side="left", padx=5)
        
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_buttons = ctk.CTkSegmentedButton(
            theme_frame,
            values=["light", "dark", "system"],
            variable=self.theme_var,
            command=self._change_theme
        )
        theme_buttons.pack(side="left", padx=5)
    
    def _create_advanced_section(self, parent) -> None:
        """Create advanced settings section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        title = ctk.CTkLabel(section, text="Advanced Generation Parameters", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Info text
        colors = get_theme_colors()
        info_text = ctk.CTkLabel(
            section,
            text="Fine-tune voice generation quality and behavior. Adjust these if audio is cut off, too robotic, or needs more variation.",
            font=("Arial", 10),
            text_color=colors["text_secondary"],
            wraplength=700
        )
        info_text.pack(pady=(0, 10))
        
        # Max new tokens
        tokens_frame = ctk.CTkFrame(section)
        tokens_frame.pack(fill="x", padx=10, pady=5)
        
        tokens_label = ctk.CTkLabel(tokens_frame, text="Max New Tokens:", width=150, anchor="w")
        tokens_label.pack(side="left", padx=5)
        
        self.tokens_entry = ctk.CTkEntry(tokens_frame, width=100)
        self.tokens_entry.insert(0, str(self.config.get("generation_params.max_new_tokens", 2048)))
        self.tokens_entry.pack(side="left", padx=5)
        
        colors = get_theme_colors()
        tokens_info = ctk.CTkLabel(
            tokens_frame,
            text="Maximum audio length (1024-4096). Increase if audio gets cut off. Higher = slower generation.",
            font=("Arial", 9),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        tokens_info.pack(side="left", padx=10, fill="x", expand=True)
        
        # Temperature
        temp_frame = ctk.CTkFrame(section)
        temp_frame.pack(fill="x", padx=10, pady=5)
        
        temp_label = ctk.CTkLabel(temp_frame, text="Temperature:", width=150, anchor="w")
        temp_label.pack(side="left", padx=5)
        
        self.temp_slider = ctk.CTkSlider(temp_frame, from_=0.1, to=1.5, number_of_steps=140, width=200)
        self.temp_slider.set(self.config.get("generation_params.temperature", 0.7))
        self.temp_slider.pack(side="left", padx=5)
        
        self.temp_value_label = ctk.CTkLabel(temp_frame, text=f"{self.temp_slider.get():.2f}", width=50)
        self.temp_value_label.pack(side="left", padx=5)
        self.temp_slider.configure(command=lambda v: self.temp_value_label.configure(text=f"{v:.2f}"))
        
        colors = get_theme_colors()
        temp_info = ctk.CTkLabel(
            temp_frame,
            text="Voice expressiveness (0.1-1.5). Low=consistent/robotic, High=varied/creative. Default: 0.7",
            font=("Arial", 9),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        temp_info.pack(side="left", padx=10, fill="x", expand=True)
        
        # Top P (nucleus sampling)
        top_p_frame = ctk.CTkFrame(section)
        top_p_frame.pack(fill="x", padx=10, pady=5)
        
        top_p_label = ctk.CTkLabel(top_p_frame, text="Top P:", width=150, anchor="w")
        top_p_label.pack(side="left", padx=5)
        
        self.top_p_slider = ctk.CTkSlider(top_p_frame, from_=0.5, to=1.0, number_of_steps=50, width=200)
        self.top_p_slider.set(self.config.get("generation_params.top_p", 0.9))
        self.top_p_slider.pack(side="left", padx=5)
        
        self.top_p_value_label = ctk.CTkLabel(top_p_frame, text=f"{self.top_p_slider.get():.2f}", width=50)
        self.top_p_value_label.pack(side="left", padx=5)
        self.top_p_slider.configure(command=lambda v: self.top_p_value_label.configure(text=f"{v:.2f}"))
        
        colors = get_theme_colors()
        top_p_info = ctk.CTkLabel(
            top_p_frame,
            text="Word choice diversity (nucleus sampling). Low=predictable, High=creative. Default: 0.9",
            font=("Arial", 9),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        top_p_info.pack(side="left", padx=10, fill="x", expand=True)
        
        # Do sample
        do_sample_frame = ctk.CTkFrame(section)
        do_sample_frame.pack(fill="x", padx=10, pady=5)
        
        do_sample_label = ctk.CTkLabel(do_sample_frame, text="Enable Sampling:", width=150, anchor="w")
        do_sample_label.pack(side="left", padx=5)
        
        self.do_sample_var = ctk.BooleanVar(value=self.config.get("generation_params.do_sample", True))
        do_sample_check = ctk.CTkCheckBox(
            do_sample_frame,
            text="",
            variable=self.do_sample_var,
            width=30
        )
        do_sample_check.pack(side="left", padx=5)
        
        colors = get_theme_colors()
        do_sample_info = ctk.CTkLabel(
            do_sample_frame,
            text="Enable randomness in generation. Almost always should be ON for natural speech.",
            font=("Arial", 9),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        do_sample_info.pack(side="left", padx=10, fill="x", expand=True)
        
        # Repetition penalty
        rep_pen_frame = ctk.CTkFrame(section)
        rep_pen_frame.pack(fill="x", padx=10, pady=5)
        
        rep_pen_label = ctk.CTkLabel(rep_pen_frame, text="Repetition Penalty:", width=150, anchor="w")
        rep_pen_label.pack(side="left", padx=5)
        
        self.rep_pen_slider = ctk.CTkSlider(rep_pen_frame, from_=0.8, to=1.5, number_of_steps=70, width=200)
        self.rep_pen_slider.set(self.config.get("generation_params.repetition_penalty", 1.0))
        self.rep_pen_slider.pack(side="left", padx=5)
        
        self.rep_pen_value_label = ctk.CTkLabel(rep_pen_frame, text=f"{self.rep_pen_slider.get():.2f}", width=50)
        self.rep_pen_value_label.pack(side="left", padx=5)
        self.rep_pen_slider.configure(command=lambda v: self.rep_pen_value_label.configure(text=f"{v:.2f}"))
        
        colors = get_theme_colors()
        rep_pen_info = ctk.CTkLabel(
            rep_pen_frame,
            text="Reduces repeated words/phrases (0.8-1.5). 1.0=no penalty, >1.0=discourage repetition. Default: 1.0",
            font=("Arial", 9),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        rep_pen_info.pack(side="left", padx=10, fill="x", expand=True)
    
    def _create_actions_section(self, parent) -> None:
        """Create action buttons section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=20)
        
        btn_frame = ctk.CTkFrame(section)
        btn_frame.pack(pady=10)
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Settings",
            command=self._save_settings,
            width=150,
            height=40,
            fg_color="green"
        )
        save_btn.pack(side="left", padx=10)
        
        reload_btn = ctk.CTkButton(
            btn_frame,
            text="Reload Models",
            command=self._reload_models,
            width=150,
            height=40
        )
        reload_btn.pack(side="left", padx=10)
        
        reset_btn = ctk.CTkButton(
            btn_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
            width=150,
            height=40,
            fg_color="darkred"
        )
        reset_btn.pack(side="left", padx=10)
    
    def _browse_directory(self, entry_widget) -> None:
        """Browse for directory."""
        directory = filedialog.askdirectory()
        if directory:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, directory)
    
    def _change_theme(self, theme: str) -> None:
        """Change application theme."""
        ctk.set_appearance_mode(theme)
        self.config.set("theme", theme)
        messagebox.showinfo("Theme Changed", f"Theme changed to: {theme}")
    
    def _validate_token(self) -> None:
        """Validate HuggingFace token."""
        colors = get_theme_colors()
        token = self.token_entry.get().strip()
        if not token:
            self.token_status_label.configure(text="❌ No token provided", text_color=colors["error_text"])
            return
        
        try:
            from huggingface_hub import whoami
            user_info = whoami(token=token)
            username = user_info.get("name", "Unknown")
            self.token_status_label.configure(text=f"✓ Valid token for user: {username}", text_color=colors["success_text"])
        except Exception as e:
            self.token_status_label.configure(text=f"❌ Invalid token: {str(e)}", text_color=colors["error_text"])
    
    def _save_token(self) -> None:
        """Save HuggingFace token."""
        colors = get_theme_colors()
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Error", "No token to save")
            return
        
        try:
            from huggingface_hub import login
            login(token=token)
            messagebox.showinfo("Success", "Token saved successfully")
            self.token_status_label.configure(text="✓ Token saved", text_color=colors["success_text"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save token: {e}")
    
    def _clear_token(self) -> None:
        """Clear HuggingFace token."""
        colors = get_theme_colors()
        response = messagebox.askyesno("Confirm", "Clear saved HuggingFace token?")
        if response:
            try:
                from huggingface_hub import logout
                logout()
                self.token_entry.delete(0, "end")
                self.token_status_label.configure(text="Token cleared", text_color=colors["text_secondary"])
                messagebox.showinfo("Success", "Token cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear token: {e}")
    
    def _save_settings(self) -> None:
        """Save all settings."""
        try:
            # Parse device selection
            device_str = self.device_combo.get()
            device_id = device_str.split(" - ")[0]
            
            # Validate generation parameters
            max_tokens = int(self.tokens_entry.get())
            if max_tokens < 1024 or max_tokens > 4096:
                raise ValueError("Max new tokens must be between 1024 and 4096")
            
            temperature = self.temp_slider.get()
            if temperature < 0.1 or temperature > 1.5:
                raise ValueError("Temperature must be between 0.1 and 1.5")
            
            top_p = self.top_p_slider.get()
            if top_p < 0.5 or top_p > 1.0:
                raise ValueError("Top P must be between 0.5 and 1.0")
            
            rep_penalty = self.rep_pen_slider.get()
            if rep_penalty < 0.8 or rep_penalty > 1.5:
                raise ValueError("Repetition penalty must be between 0.8 and 1.5")
            
            # Save settings (active_model is managed by the Active Model switcher)
            self.config.set("device", device_id, save=False)
            self.config.set("use_flash_attention", self.flash_var.get(), save=False)
            
            # Only save output_dir if not using workspace manager (legacy mode)
            if hasattr(self, 'output_entry'):
                self.config.set("output_dir", self.output_entry.get(), save=False)
            
            self.config.set("generation_params.max_new_tokens", max_tokens, save=False)
            self.config.set("generation_params.temperature", temperature, save=False)
            self.config.set("generation_params.top_p", top_p, save=False)
            self.config.set("generation_params.do_sample", self.do_sample_var.get(), save=False)
            self.config.set("generation_params.repetition_penalty", rep_penalty, save=False)
            
            self.config.save()
            
            messagebox.showinfo("Success", "Settings saved!\n\nReload models for changes to take effect.")
            
        except ValueError as e:
            logger.error(f"Invalid parameter value: {e}")
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _manage_models(self) -> None:
        """Open model management dialog to download/manage models."""
        from gui.model_selection_dialog import show_model_selection_dialog
        
        logger.info("User opened model management dialog")
        
        # Backup current config in case of failure
        old_downloaded_models = self.config.get("downloaded_models", [])
        old_active_model = self.config.get("active_model", None)
        old_device = self.config.get("device", "cuda:0")
        
        model_selection = show_model_selection_dialog()
        
        # User cancelled dialog
        if not model_selection:
            logger.info("User cancelled model management dialog")
            return
        
        # User chose to skip
        if model_selection["skip"]:
            logger.info("User chose to skip model management")
            return
        
        models_to_download = model_selection["models"]
        new_active_model = model_selection["active_model"]
        new_device = model_selection["device"]
        
        logger.info(f"Model selection: {models_to_download}, active: {new_active_model}")
        
        # Check if download callback is available
        if not self.download_callback:
            logger.error("Download callback not available")
            messagebox.showerror(
                "Error",
                "Model download functionality is not available.\n"
                "Please restart the application."
            )
            return
        
        # Update config first
        self.config.set("downloaded_models", models_to_download, save=False)
        self.config.set("active_model", new_active_model, save=False)
        self.config.set("device", new_device, save=True)
        
        # Trigger download through callback (this will handle the actual download)
        try:
            logger.info("Triggering model download...")
            self.download_callback(models_to_download, new_active_model)
            
            # Refresh UI to show new status
            self.after(100, self._refresh_model_selection_ui)
            
            logger.info("Model download initiated successfully")
            
        except Exception as e:
            logger.error(f"Model download failed: {e}", exc_info=True)
            
            # Revert config on failure
            logger.warning("Reverting config to previous state")
            self.config.set("downloaded_models", old_downloaded_models, save=False)
            self.config.set("active_model", old_active_model, save=False)
            self.config.set("device", old_device, save=True)
            
            # Refresh UI to show reverted status
            self._refresh_model_selection_ui()
            
            messagebox.showerror(
                "Download Failed",
                f"Failed to download models:\n\n{str(e)}\n\n"
                "Configuration has been reverted to previous state."
            )
    
    def _reload_models(self) -> None:
        """Trigger model reload."""
        if self.reload_callback:
            self.reload_callback()
    
    def _reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        response = messagebox.askyesno(
            "Reset Settings",
            "Reset all settings to default values?\nThis will require reloading models."
        )
        
        if response:
            self.config.reset_to_defaults()
            messagebox.showinfo("Success", "Settings reset to defaults.\n\nPlease restart the application.")
