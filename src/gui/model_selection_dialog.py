"""Model selection dialog for first launch."""

import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
from typing import Optional, List, Dict
import os

from utils.error_handler import logger


class ModelSelectionDialog(ctk.CTkToplevel):
    """Dialog for selecting which models to download on first launch."""
    
    def __init__(self, parent=None):
        """Initialize model selection dialog.
        
        Args:
            parent: Parent window (None for standalone)
        """
        super().__init__(parent)
        
        self.title("Model Selection - Qwen-semble")
        self.geometry("800x700")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.result = None  # Will store selected models
        
        # State variables
        self.selection = ctk.StringVar(value="1.7B")
        
        # Detect system capabilities
        self.system_info = self._detect_system()
        self.recommendation = self._get_recommendation()
        
        self._create_ui()
    
    def _detect_system(self) -> Dict:
        """Detect system GPU/CPU capabilities.
        
        Returns:
            Dictionary with system information
        """
        info = {
            "has_cuda": False,
            "gpu_name": "N/A",
            "gpu_vram_gb": 0,
            "cpu_ram_gb": 0,
            "device": "cpu"
        }
        
        try:
            import torch
            import psutil
            
            # Check CUDA availability
            if torch.cuda.is_available():
                info["has_cuda"] = True
                info["device"] = "cuda:0"
                info["gpu_name"] = torch.cuda.get_device_name(0)
                
                # Get VRAM in GB
                gpu_props = torch.cuda.get_device_properties(0)
                info["gpu_vram_gb"] = gpu_props.total_memory / (1024**3)
            
            # Get CPU RAM in GB
            info["cpu_ram_gb"] = psutil.virtual_memory().total / (1024**3)
            
            logger.info(f"System detection: {info}")
            
        except Exception as e:
            logger.error(f"Error detecting system: {e}")
        
        return info
    
    def _get_recommendation(self) -> str:
        """Get recommended model based on system capabilities.
        
        Returns:
            Recommended option: "1.7B", "0.6B", or "both"
        """
        if self.system_info["has_cuda"]:
            vram = self.system_info["gpu_vram_gb"]
            
            if vram >= 12:
                return "both"  # High-end GPU, can handle both
            elif vram >= 6:
                return "1.7B"  # Mid-range GPU, use larger model
            else:
                return "0.6B"  # Low VRAM, use smaller model
        else:
            # CPU mode - check RAM
            ram = self.system_info["cpu_ram_gb"]
            
            if ram >= 16:
                return "1.7B"  # Enough RAM for larger model
            else:
                return "0.6B"  # Limited RAM, use smaller model
    
    def _create_ui(self):
        """Create dialog UI."""
        # Create scrollable content area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # Title section
        self._create_title_section()
        
        # System info section
        self._create_system_info_section()
        
        # Model options
        self._create_model_options()
        
        # Buttons (always visible at bottom)
        self._create_buttons()
    
    def _create_title_section(self):
        """Create title section."""
        title_frame = ctk.CTkFrame(self.scroll_frame)
        title_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        title = ctk.CTkLabel(
            title_frame,
            text="🤖 Model Selection",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=(10, 5))
        
        subtitle = ctk.CTkLabel(
            title_frame,
            text="Choose which AI model(s) to download for voice synthesis.\n"
                 "You can change this later in Settings.",
            font=("Arial", 12),
            text_color="gray"
        )
        subtitle.pack(pady=(0, 10))
    
    def _create_system_info_section(self):
        """Create system information section."""
        sys_frame = ctk.CTkFrame(self.scroll_frame)
        sys_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(sys_frame, text="System Detection", font=("Arial", 14, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Build info text
        if self.system_info["has_cuda"]:
            info_text = (
                f"✓ GPU: {self.system_info['gpu_name']}\n"
                f"✓ VRAM: {self.system_info['gpu_vram_gb']:.1f} GB\n"
                f"✓ RAM: {self.system_info['cpu_ram_gb']:.1f} GB\n"
                f"✓ Device: {self.system_info['device']}"
            )
        else:
            info_text = (
                f"⚠ GPU: Not available (CPU mode)\n"
                f"✓ RAM: {self.system_info['cpu_ram_gb']:.1f} GB\n"
                f"✓ Device: CPU"
            )
        
        info_label = ctk.CTkLabel(
            sys_frame,
            text=info_text,
            font=("Arial", 11),
            text_color="lightblue",
            anchor="w",
            justify="left"
        )
        info_label.pack(anchor="w", padx=10, pady=(0, 10))
    
    def _create_model_options(self):
        """Create model selection options."""
        options_frame = ctk.CTkFrame(self.scroll_frame)
        options_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(options_frame, text="Select Model(s)", font=("Arial", 14, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Option 1: 1.7B Model
        self._create_option(
            options_frame,
            value="1.7B",
            title="Qwen3-TTS 1.7B (Recommended)",
            details=[
                "Size: ~7 GB download",
                "Quality: High",
                "Speed: Moderate",
                f"VRAM: ~8 GB (GPU) / RAM: ~8 GB (CPU)",
                "Best for: High-quality voices, production use"
            ],
            recommended=(self.recommendation == "1.7B")
        )
        
        # Option 2: 0.6B Model
        self._create_option(
            options_frame,
            value="0.6B",
            title="Qwen3-TTS 0.6B (Faster)",
            details=[
                "Size: ~3 GB download",
                "Quality: Good",
                "Speed: Fast",
                f"VRAM: ~3 GB (GPU) / RAM: ~4 GB (CPU)",
                "Best for: Quick experiments, low-end hardware"
            ],
            recommended=(self.recommendation == "0.6B")
        )
        
        # Option 3: Both Models
        self._create_option(
            options_frame,
            value="both",
            title="Both Models",
            details=[
                "Size: ~10 GB total download",
                "Gives you flexibility to switch based on needs",
                "Can choose which to use in Settings tab",
                "Recommended if you have sufficient disk space"
            ],
            recommended=(self.recommendation == "both")
        )
        
        # Option 4: Skip
        self._create_option(
            options_frame,
            value="skip",
            title="Skip for Now",
            details=[
                "Download models later from Settings tab",
                "Application UI will be available",
                "⚠ TTS features will be disabled until models are loaded",
                "No disk space used now"
            ],
            recommended=False
        )
    
    def _create_option(self, parent, value: str, title: str, details: List[str], recommended: bool):
        """Create a single model option.
        
        Args:
            parent: Parent widget
            value: Option value
            title: Option title
            details: List of detail strings
            recommended: Whether this is the recommended option
        """
        option_frame = ctk.CTkFrame(parent)
        option_frame.pack(fill="x", padx=10, pady=5)
        
        # Radio button with title
        header_frame = ctk.CTkFrame(option_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        radio = ctk.CTkRadioButton(
            header_frame,
            text=title,
            variable=self.selection,
            value=value,
            font=("Arial", 13, "bold")
        )
        radio.pack(side="left")
        
        if recommended:
            rec_label = ctk.CTkLabel(
                header_frame,
                text="⭐ Recommended for your system",
                font=("Arial", 11, "bold"),
                text_color="gold"
            )
            rec_label.pack(side="left", padx=10)
        
        # Details
        for detail in details:
            detail_label = ctk.CTkLabel(
                option_frame,
                text=f"  • {detail}",
                font=("Arial", 10),
                text_color="gray",
                anchor="w"
            )
            detail_label.pack(anchor="w", padx=20, pady=1)
        
        # Spacing
        ctk.CTkLabel(option_frame, text="", height=5).pack()
    
    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=15, side="bottom")
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=120,
            height=40,
            fg_color="gray"
        )
        cancel_btn.pack(side="right", padx=5)
        
        download_btn = ctk.CTkButton(
            button_frame,
            text="✓ Continue",
            command=self._on_continue,
            width=180,
            height=40,
            fg_color="green",
            font=("Arial", 14, "bold")
        )
        download_btn.pack(side="right", padx=5)
    
    def _on_cancel(self):
        """Handle cancel button."""
        logger.info("Model selection cancelled by user")
        self.result = None
        self.destroy()
    
    def _on_continue(self):
        """Handle continue button."""
        selection = self.selection.get()
        
        logger.info(f"User selected: {selection}")
        
        # Determine which models to download
        if selection == "skip":
            models = []
        elif selection == "both":
            models = ["1.7B", "0.6B"]
        else:
            models = [selection]
        
        # Set default active model
        if models:
            # Default to 1.7B if available, otherwise first in list
            active_model = "1.7B" if "1.7B" in models else models[0]
        else:
            active_model = None
        
        self.result = {
            "models": models,
            "active_model": active_model,
            "device": self.system_info["device"],
            "skip": (selection == "skip")
        }
        
        logger.info(f"Model selection result: {self.result}")
        self.destroy()


def show_model_selection_dialog() -> Optional[Dict]:
    """Show model selection dialog and return result.
    
    Returns:
        Dictionary with model selection or None if cancelled
    """
    # Create a temporary root window if needed
    root = ctk.CTk()
    root.withdraw()
    
    dialog = ModelSelectionDialog(root)
    root.wait_window(dialog)
    
    result = dialog.result
    root.destroy()
    
    return result
