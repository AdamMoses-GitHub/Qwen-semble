"""Workspace setup dialog for first launch."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional
import shutil

from utils.workspace_manager import WorkspaceManager
from utils.error_handler import logger


class WorkspaceSetupDialog(ctk.CTkToplevel):
    """Dialog for setting up workspace directory on first launch."""
    
    def __init__(self, parent=None):
        """Initialize workspace setup dialog.
        
        Args:
            parent: Parent window (None for standalone)
        """
        super().__init__(parent)
        
        self.title("Workspace Setup - Qwen-semble")
        self.geometry("700x600")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.workspace_manager = WorkspaceManager()
        self.result = None  # Will store selected workspace path
        
        # State variables
        self.selected_path = ctk.StringVar(value="./working")
        
        self._create_ui()
        
        # Update preview when path changes
        self.selected_path.trace_add("write", lambda *args: self._update_preview())
    
    def _create_ui(self):
        """Create dialog UI."""
        # Create scrollable content area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # Welcome section
        self._create_welcome_section()
        
        # Path selection section
        self._create_path_section()
        
        # Disk space info
        self._create_disk_space_section()
        
        # Buttons (always visible at bottom, outside scrollable area)
        self._create_buttons()
    
    def _create_welcome_section(self):
        """Create welcome message section."""
        welcome_frame = ctk.CTkFrame(self.scroll_frame)
        welcome_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        title = ctk.CTkLabel(
            welcome_frame,
            text="🎙️ Welcome to Qwen-semble!",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=(10, 5))
        
        message = ctk.CTkLabel(
            welcome_frame,
            text="Before we begin, let's set up your workspace.\n"
                 "Your voices, narrations, and settings will be stored here.\n"
                 "(AI models are cached separately in the system cache)",
            font=("Arial", 12),
            text_color="gray"
        )
        message.pack(pady=(0, 10))
    
    def _create_path_section(self):
        """Create workspace path selection section."""
        path_frame = ctk.CTkFrame(self.scroll_frame)
        path_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(path_frame, text="Workspace Location", font=("Arial", 14, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Path input with browse button
        input_frame = ctk.CTkFrame(path_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        self.path_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.selected_path,
            width=450,
            placeholder_text="Enter workspace path..."
        )
        self.path_entry.pack(side="left", padx=5, pady=5)
        
        browse_btn = ctk.CTkButton(
            input_frame,
            text="Browse...",
            command=self._browse_directory,
            width=100
        )
        browse_btn.pack(side="left", padx=5)
        
        # Preview
        preview_frame = ctk.CTkFrame(path_frame)
        preview_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        preview_label = ctk.CTkLabel(preview_frame, text="Full path:", font=("Arial", 11))
        preview_label.pack(anchor="w", padx=5)
        
        self.preview_text = ctk.CTkLabel(
            preview_frame,
            text="",
            font=("Arial", 10),
            text_color="gray",
            anchor="w"
        )
        self.preview_text.pack(anchor="w", padx=5, pady=(0, 5))
        
        self._update_preview()
    
    def _create_disk_space_section(self):
        """Create disk space information section."""
        space_frame = ctk.CTkFrame(self.scroll_frame)
        space_frame.pack(fill="x", padx=10, pady=10)
        
        title = ctk.CTkLabel(space_frame, text="Disk Space Requirements", font=("Arial", 14, "bold"))
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        min_gb, rec_gb = self.workspace_manager.get_estimated_space_gb()
        
        info_text = (
            f"Workspace (user data):\n"
            f"• Minimum: ~{min_gb:.0f} GB (basic operation)\n"
            f"• Recommended: ~{rec_gb:.0f} GB (comfortable use)\n"
            f"• Includes: voices, narrations, logs\n\n"
            f"AI Models (cached separately):\n"
            f"• ~7-14 GB in system cache\n"
            f"• Location: {Path.home() / '.cache' / 'huggingface'}"
        )
        
        info_label = ctk.CTkLabel(
            space_frame,
            text=info_text,
            font=("Arial", 11),
            text_color="gray",
            anchor="w",
            justify="left"
        )
        info_label.pack(anchor="w", padx=10, pady=(0, 10))
    
    def _create_buttons(self):
        """Create dialog buttons (fixed at bottom, always visible)."""
        # Fixed button frame outside scrollable area
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
        
        create_btn = ctk.CTkButton(
            button_frame,
            text="✓ Create Workspace",
            command=self._on_create,
            width=180,
            height=40,
            fg_color="green",
            font=("Arial", 14, "bold")
        )
        create_btn.pack(side="right", padx=5)
    
    def _browse_directory(self):
        """Open directory browser."""
        initial_dir = Path.home()
        
        directory = filedialog.askdirectory(
            title="Select Workspace Location",
            initialdir=initial_dir
        )
        
        if directory:
            self.selected_path.set(directory)
    
    def _update_preview(self):
        """Update the path preview."""
        try:
            path_str = self.selected_path.get()
            resolved_path = Path(path_str).resolve()
            self.preview_text.configure(text=str(resolved_path))
            
        except Exception as e:
            self.preview_text.configure(text=f"Error: {e}")
    
    def _on_cancel(self):
        """Handle cancel button."""
        logger.info("Workspace setup cancelled by user")
        self.result = None
        self.destroy()
    
    def _on_create(self):
        """Handle create button."""
        try:
            path_str = self.selected_path.get().strip()
            if not path_str:
                messagebox.showerror("Error", "Please enter a workspace path.")
                return
            
            # Resolve to absolute path
            workspace_path = Path(path_str).resolve()
            
            # Validate path
            is_valid, error_msg = self.workspace_manager.validate_workspace(workspace_path)
            if not is_valid:
                messagebox.showerror("Invalid Path", error_msg)
                return
            
            # Check disk space if path exists
            if workspace_path.parent.exists():
                try:
                    stat = shutil.disk_usage(workspace_path.parent)
                    available_gb = stat.free / (1024**3)
                    min_gb, _ = self.workspace_manager.get_estimated_space_gb()
                    
                    if available_gb < min_gb:
                        response = messagebox.askyesno(
                            "Low Disk Space",
                            f"Available space: {available_gb:.1f} GB\n"
                            f"Minimum required: {min_gb:.0f} GB\n\n"
                            "Continue anyway?"
                        )
                        if not response:
                            return
                except:
                    pass  # Ignore disk space check errors
            
            # Create workspace structure
            if not self.workspace_manager.create_workspace_structure(workspace_path):
                messagebox.showerror("Error", "Failed to create workspace structure.")
                return
            
            # Save configuration (absolute path as string)
            self.workspace_manager.save_config(str(workspace_path))
            
            self.result = {'path': workspace_path}
            
            logger.info(f"Workspace created successfully at: {workspace_path}")
            messagebox.showinfo(
                "Success",
                f"Workspace created successfully!\n\nLocation: {workspace_path}\n\n"
                "The application will now start."
            )
            
            self.destroy()
            
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to create workspace:\n{e}")


def show_workspace_setup_dialog() -> Optional[dict]:
    """Show workspace setup dialog and return result.
    
    Returns:
        Dictionary with workspace configuration or None if cancelled
    """
    # Create a temporary root window if needed
    root = ctk.CTk()
    root.withdraw()
    
    dialog = WorkspaceSetupDialog(root)
    root.wait_window(dialog)
    
    result = dialog.result
    root.destroy()
    
    return result
