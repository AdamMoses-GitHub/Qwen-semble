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
    
    def __init__(self, parent, tts_engine, config, reload_callback, workspace_mgr: Optional['WorkspaceManager'] = None):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.config = config
        self.reload_callback = reload_callback
        self.workspace_mgr = workspace_mgr
        
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
        
        title = ctk.CTkLabel(section, text="Model Configuration", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
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
        
        # Model size
        size_frame = ctk.CTkFrame(section)
        size_frame.pack(fill="x", padx=10, pady=5)
        
        size_label = ctk.CTkLabel(size_frame, text="Model Size:", width=150)
        size_label.pack(side="left", padx=5)
        
        self.model_size_var = ctk.StringVar(value=self.config.get("model_size", "1.7B"))
        size_1_7b = ctk.CTkRadioButton(
            size_frame,
            text="1.7B (higher quality, ~7GB VRAM)",
            variable=self.model_size_var,
            value="1.7B"
        )
        size_1_7b.pack(side="left", padx=10)
        
        size_0_6b = ctk.CTkRadioButton(
            size_frame,
            text="0.6B (faster, ~2.5GB VRAM)",
            variable=self.model_size_var,
            value="0.6B"
        )
        size_0_6b.pack(side="left", padx=10)
        
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
    
    def _create_auth_section(self, parent) -> None:
        """Create HuggingFace authentication section."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=10)
        
        title = ctk.CTkLabel(section, text="HuggingFace Authentication", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        info_label = ctk.CTkLabel(
            section,
            text="Required for downloading models. Get your token at huggingface.co/settings/tokens",
            text_color="gray"
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
        info_text = ctk.CTkLabel(
            section,
            text="Fine-tune voice generation quality and behavior. Adjust these if audio is cut off, too robotic, or needs more variation.",
            font=("Arial", 10),
            text_color="gray",
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
        
        tokens_info = ctk.CTkLabel(
            tokens_frame,
            text="Maximum audio length (1024-4096). Increase if audio gets cut off. Higher = slower generation.",
            font=("Arial", 9),
            text_color="gray",
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
        
        temp_info = ctk.CTkLabel(
            temp_frame,
            text="Voice expressiveness (0.1-1.5). Low=consistent/robotic, High=varied/creative. Default: 0.7",
            font=("Arial", 9),
            text_color="gray",
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
        
        top_p_info = ctk.CTkLabel(
            top_p_frame,
            text="Word choice diversity (nucleus sampling). Low=predictable, High=creative. Default: 0.9",
            font=("Arial", 9),
            text_color="gray",
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
        
        do_sample_info = ctk.CTkLabel(
            do_sample_frame,
            text="Enable randomness in generation. Almost always should be ON for natural speech.",
            font=("Arial", 9),
            text_color="gray",
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
        
        rep_pen_info = ctk.CTkLabel(
            rep_pen_frame,
            text="Reduces repeated words/phrases (0.8-1.5). 1.0=no penalty, >1.0=discourage repetition. Default: 1.0",
            font=("Arial", 9),
            text_color="gray",
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
            
            # Save settings
            self.config.set("device", device_id, save=False)
            self.config.set("model_size", self.model_size_var.get(), save=False)
            self.config.set("use_flash_attention", self.flash_var.get(), save=False)
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
